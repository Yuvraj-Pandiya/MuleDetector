"""
app/routers/predict.py
=======================
Prediction and explainability endpoints.

GET /risk-scores             — score all accounts in the feature source,
                               return sorted by risk_score descending.
GET /explain/{account_id}    — SHAP explanation for a single account.

TODO (sync-point): swap _MOCK_CSV for the real /features endpoint output
once the data-pipeline team delivers it.  The calls to score_accounts()
and explain_account() do not change; only the DataFrame source changes.
"""

from __future__ import annotations

import logging
import pathlib
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException

from app.services.feature_pipeline import build_feature_matrix

from app.services.explainer import explain_account
from app.services.risk_scorer import score_accounts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predict", tags=["prediction"])

# ---------------------------------------------------------------------------
# Data source
# ---------------------------------------------------------------------------
_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"

# TODO (sync-point): replace with the real pipeline output path / call.
_TRANSACTIONS_CSV = _DATA_DIR / "transactions.csv"


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------

def _load_feature_df() -> pd.DataFrame:
    """Load feature DataFrame from transactions.csv (or mock_features.csv fallback)."""
    if _TRANSACTIONS_CSV.exists():
        from app.services.feature_pipeline import build_feature_matrix
        return build_feature_matrix(_TRANSACTIONS_CSV)
    
    mock_csv = _DATA_DIR / "mock_features.csv"
    if not mock_csv.exists():
        from app.services.mock_generator import generate_mock_features_csv
        generate_mock_features_csv(mock_csv)
    return pd.read_csv(mock_csv)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/risk-scores",
    summary="Score accounts with server-side pagination, filtering, search, and sorting",
    response_description="Paginated list of account risk objects with totals and metadata.",
)
def get_risk_scores(
    tier: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    anomaly_only: Optional[bool] = None,
    min_network_risk: Optional[float] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_by: Optional[str] = "highest_risk",
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=200),
) -> dict[str, Any]:
    """
    Load the feature matrix and score accounts.
    Supports server-side pagination, filtering, search across account/sender/receiver IDs, and sorting.
    """
    df = _load_feature_df()

    try:
        scored = score_accounts(df)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("score_accounts failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Scoring failed: {exc}") from exc

    records = scored.copy()
    if "top_features" in records.columns:
        records["top_features"] = records["top_features"].apply(list)

    # 1. Search Filter (account_id, sender_account_id, receiver_account_id)
    if search and search.strip():
        q = search.strip().lower()
        mask = records["account_id"].str.lower().str.contains(q)
        if "sender_account_id" in records.columns:
            mask |= records["sender_account_id"].astype(str).str.lower().str.contains(q)
        if "receiver_account_id" in records.columns:
            mask |= records["receiver_account_id"].astype(str).str.lower().str.contains(q)
        records = records[mask]

    # 2. Risk Tier Filter
    if tier and tier.strip():
        t = tier.strip().lower()
        records = records[records["risk_tier"].str.lower() == t]

    # 3. Score Range Filter
    if min_score is not None:
        records = records[records["risk_score"] >= min_score]
    if max_score is not None:
        records = records[records["risk_score"] <= max_score]

    # 4. Anomaly Flag Filter
    if anomaly_only:
        records = records[records["anomaly_score"] >= 0.5]

    # 5. Network Risk Filter
    if min_network_risk is not None:
        records = records[records["network_risk_score"] >= min_network_risk]

    # 6. Investigation Status Filter
    if status and status.strip() and status.strip().upper() != "ALL":
        st = status.strip().upper()
        records = records[records["investigation_status"].str.upper() == st]

    # 7. Date Range Filter (on last_activity)
    if start_date:
        records = records[records["last_activity"] >= start_date]
    if end_date:
        records = records[records["last_activity"] <= end_date]

    # 8. Server-side Sorting
    sort_key = (sort_by or "highest_risk").lower()
    if sort_key in ("highest_risk", "risk_desc"):
        records = records.sort_values("risk_score", ascending=False)
    elif sort_key in ("lowest_risk", "risk_asc"):
        records = records.sort_values("risk_score", ascending=True)
    elif sort_key in ("highest_anomaly", "anomaly_desc"):
        records = records.sort_values("anomaly_score", ascending=False)
    elif sort_key in ("highest_velocity", "velocity_desc"):
        records = records.sort_values("transaction_count", ascending=False)
    elif sort_key in ("highest_network_risk", "network_desc"):
        records = records.sort_values("network_risk_score", ascending=False)
    elif sort_key in ("newest_alerts", "alerts_desc"):
        records = records.sort_values(["alert_count", "risk_score"], ascending=[False, False])

    # 9. Server-side Pagination
    total_count = len(records)
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_records = records.iloc[start_idx:end_idx]

    return {
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "count": len(page_records),
        "accounts": page_records.to_dict(orient="records"),
    }



@router.get(
    "/explain/{account_id}",
    summary="Explain risk score for a single account",
    response_description=(
        "Top 5 SHAP features and a human-readable reason string "
        "for the given account."
    ),
)
def get_explanation(account_id: str) -> dict[str, Any]:
    """
    Return a SHAP-based explanation for the risk score of `account_id`.

    - **account_id**: the unique account identifier (e.g. `ACC000042`).

    Requires a trained model (`app/data/model.pkl`) — call POST /train first.
    """
    df = _load_feature_df()

    try:
        explanation = explain_account(account_id, df)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"account_id '{account_id}' not found in feature data.",
        ) from exc
    except Exception as exc:
        logger.exception("explain_account failed for %s: %s", account_id, exc)
        raise HTTPException(status_code=500, detail=f"Explanation failed: {exc}") from exc

    return explanation
