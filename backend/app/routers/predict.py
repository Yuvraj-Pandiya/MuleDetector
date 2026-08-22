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
        return build_feature_matrix(_TRANSACTIONS_CSV)
    
    mock_csv = _DATA_DIR / "mock_features.csv"
    if not mock_csv.exists():
        from scripts.generate_mock_features import main as gen_mock
        gen_mock()
    return pd.read_csv(mock_csv)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/risk-scores",
    summary="Score all accounts",
    response_description=(
        "List of accounts sorted by risk_score descending, each with "
        "risk_tier and the top 3 contributing features."
    ),
)
def get_risk_scores() -> dict[str, Any]:
    """
    Load the feature matrix and score every account.

    Returns accounts sorted by **risk_score descending** so the highest-risk
    accounts appear first.

    Requires a trained model (`app/data/model.pkl`) — call POST /train first.
    """
    df = _load_feature_df()

    try:
        scored = score_accounts(df)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("score_accounts failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Scoring failed: {exc}") from exc

    # Convert top_features lists to plain lists for JSON serialisation
    records = scored.copy()
    records["top_features"] = records["top_features"].apply(list)

    return {
        "count": len(records),
        "accounts": records.to_dict(orient="records"),
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
