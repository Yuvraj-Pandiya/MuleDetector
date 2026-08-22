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
    "/anomalies",
    summary="Get Isolation Forest anomaly detection summary and account breakdown",
    response_description="Anomaly summary KPIs, score distribution histogram, and account anomaly records.",
)
def get_anomaly_summary(
    min_anomaly: Optional[float] = None,
    sort_by: Optional[str] = "highest_anomaly",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=15, ge=1, le=200),
) -> dict[str, Any]:
    """
    Computes Isolation Forest anomaly detection metrics across all accounts.
    Returns:
      - total_accounts_analyzed
      - anomalous_accounts
      - anomaly_rate
      - average_anomaly_score
      - high_anomaly_accounts
      - anomaly_distribution (histogram buckets)
      - account table with: account_id, anomaly_score, risk_score, transaction_velocity, behavior_change, network_risk
    """
    df = _load_feature_df()

    try:
        scored = score_accounts(df)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("score_accounts failed in get_anomaly_summary: %s", exc)
        raise HTTPException(status_code=500, detail=f"Anomaly query failed: {exc}") from exc

    total_count = len(scored)
    if total_count == 0:
        return {
            "total_accounts_analyzed": 0,
            "anomalous_accounts": 0,
            "anomaly_rate": 0.0,
            "average_anomaly_score": 0.0,
            "high_anomaly_accounts": 0,
            "distribution": [],
            "accounts": [],
        }

    # Extract anomaly scores produced by Isolation Forest / backend anomaly service
    anomaly_scores = scored["anomaly_score"].values
    avg_anomaly = float(np.mean(anomaly_scores))
    anomalous_cnt = int(np.sum(anomaly_scores >= 0.50))
    high_anomalous_cnt = int(np.sum(anomaly_scores >= 0.70))
    anomaly_rate = round((anomalous_cnt / total_count) * 100.0, 2)

    # Compute Anomaly Score Distribution histogram (5 buckets: 0.0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0)
    bins = [0.0, 0.2, 0.4, 0.6, 0.8, 1.05]
    counts, _ = np.histogram(anomaly_scores, bins=bins)
    distribution = [
        {"range": "0.0 - 0.2 (Normal)", "count": int(counts[0]), "tier": "Low"},
        {"range": "0.2 - 0.4 (Mild)", "count": int(counts[1]), "tier": "Low"},
        {"range": "0.4 - 0.6 (Moderate)", "count": int(counts[2]), "tier": "Medium"},
        {"range": "0.6 - 0.8 (Elevated)", "count": int(counts[3]), "tier": "High"},
        {"range": "0.8 - 1.0 (Critical)", "count": int(counts[4]), "tier": "Critical"},
    ]

    # Map account level fields
    records = []
    for _, row in scored.iterrows():
        # Extract transaction velocity (txn_count_1h or transaction_count)
        velocity = row.get("txn_count_1h", row.get("transaction_count", 0))
        
        # Extract behavior change (recent_vs_historical_transaction_ratio or transaction_velocity_change)
        bev_change = row.get("transaction_velocity_change", row.get("recent_vs_historical_transaction_ratio", 1.0))
        if pd.isna(bev_change):
            bev_change = 1.0
        
        net_risk = row.get("network_risk_score", 0.0)

        records.append({
            "account_id": str(row["account_id"]),
            "anomaly_score": round(float(row["anomaly_score"]), 3),
            "risk_score": round(float(row["risk_score"]), 1) if float(row["risk_score"]) > 1.0 else round(float(row["risk_score"]) * 100.0, 1),
            "transaction_velocity": int(velocity),
            "behavior_change": round(float(bev_change), 2),
            "network_risk": round(float(net_risk), 1),
        })

    # Apply min_anomaly filter if provided
    if min_anomaly is not None:
        records = [r for r in records if r["anomaly_score"] >= min_anomaly]

    # Sort records
    if sort_by == "highest_anomaly":
        records.sort(key=lambda x: x["anomaly_score"], reverse=True)
    elif sort_by == "highest_risk":
        records.sort(key=lambda x: x["risk_score"], reverse=True)
    elif sort_by == "highest_velocity":
        records.sort(key=lambda x: x["transaction_velocity"], reverse=True)
    elif sort_by == "highest_behavior":
        records.sort(key=lambda x: x["behavior_change"], reverse=True)

    # Server-side pagination
    paginated_total = len(records)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_records = records[start_idx:end_idx]

    return {
        "total_accounts_analyzed": total_count,
        "anomalous_accounts": anomalous_cnt,
        "anomaly_rate": anomaly_rate,
        "average_anomaly_score": round(avg_anomaly, 3),
        "high_anomaly_accounts": high_anomalous_cnt,
        "distribution": distribution,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (paginated_total + page_size - 1) // page_size),
        "accounts": page_records,
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

