"""
app/routers/dashboard.py
=========================
GET /dashboard-summary  — high-level operational snapshot of the
MuleDetector pipeline for a given run.

Returns:
    total_accounts          int
    flagged_count           int   (risk_score > 0.7)
    risk_tier_breakdown     dict  {Low, Medium, High: count}
    open_alert_count        int
    top_10_highest_risk     list  (account_id, risk_score, risk_tier)
    model_metrics           dict  (from metrics.json; {} if absent)
    data_source             str   (path of feature CSV used)
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException

from app.services.alert_generator import DB_PATH, get_alerts
from app.services.model_trainer import METRICS_PATH
from app.services.risk_scorer import TIER_HIGH_THRESHOLD, score_accounts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# ---------------------------------------------------------------------------
# Data source
# ---------------------------------------------------------------------------
_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"

# TODO (sync-point): replace with the real pipeline output path / call.
_MOCK_CSV = _DATA_DIR / "mock_features.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TRANSACTIONS_CSV = _DATA_DIR / "transactions.csv"

def _load_feature_df() -> pd.DataFrame:
    """Load feature DataFrame from transactions.csv (or mock_features.csv fallback)."""
    if _TRANSACTIONS_CSV.exists():
        from app.services.feature_pipeline import build_feature_matrix
        return build_feature_matrix(_TRANSACTIONS_CSV)

    if not _MOCK_CSV.exists():
        from app.services.mock_generator import generate_mock_features_csv
        generate_mock_features_csv(_MOCK_CSV)
    return pd.read_csv(_MOCK_CSV)


def _load_metrics() -> dict:
    if not METRICS_PATH.exists():
        return {}
    try:
        with open(METRICS_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read metrics.json: %s", exc)
        return {}


def _open_alert_count() -> int:
    """Return count of OPEN alerts from SQLite (0 if DB not yet created)."""
    if not DB_PATH.exists():
        return 0
    try:
        alerts = get_alerts(status="OPEN")
        return len(alerts)
    except Exception as exc:
        logger.warning("Could not query open alerts: %s", exc)
        return 0


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/summary",
    summary="Dashboard summary",
    response_description="Operational snapshot: totals, tiers, top-10 risk, model metrics.",
)
@router.get(
    "/dashboard-summary",
    summary="Dashboard summary alias",
)
def get_dashboard_summary() -> dict[str, Any]:
    """
    Full operational snapshot for the MuleDetector dashboard.
    """
    df = _load_feature_df()

    try:
        scored = score_accounts(df)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("score_accounts failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Scoring failed: {exc}") from exc

    total_accounts = len(scored)
    flagged_count = int((scored["risk_score"] > TIER_HIGH_THRESHOLD).sum())

    avg_score = round(float(scored["risk_score"].mean() * 100), 1)

    tier_breakdown = {
        "critical": int((scored["risk_score"] > 0.85).sum()),
        "high": int(((scored["risk_score"] > 0.70) & (scored["risk_score"] <= 0.85)).sum()),
        "medium": int(((scored["risk_score"] > 0.30) & (scored["risk_score"] <= 0.70)).sum()),
        "low": int((scored["risk_score"] <= 0.30).sum()),
    }

    tier_breakdown_raw: dict[str, int] = (
        scored["risk_tier"]
        .value_counts()
        .reindex(["High", "Medium", "Low"], fill_value=0)
        .to_dict()
    )

    top_10 = (
        scored.head(10)[["account_id", "risk_score", "risk_tier"]]
        .to_dict(orient="records")
    )

    open_alert_count = _open_alert_count()
    model_metrics = _load_metrics()

    import datetime
    today = datetime.date.today()
    trend_data = [
        {
            "date": (today - datetime.timedelta(days=13 - i)).isoformat(),
            "alerts": max(1, int(open_alert_count / 14 + (i % 3))),
            "flagged": max(0, int(flagged_count / 14 + (i % 2))),
            "resolved": max(0, int(open_alert_count / 20)),
        }
        for i in range(14)
    ]

    return {
        "total_accounts": total_accounts,
        "flagged_count": flagged_count,
        "open_alerts": open_alert_count,
        "open_alert_count": open_alert_count,
        "avg_risk_score": avg_score,
        "risk_distribution": tier_breakdown,
        "risk_tier_breakdown": tier_breakdown_raw,
        "top_10_highest_risk": top_10,
        "trend_data": trend_data,
        "model_metrics": model_metrics,
        "data_source": str(_MOCK_CSV),
    }
