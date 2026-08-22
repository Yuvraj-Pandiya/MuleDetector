"""
app/routers/alerts.py
======================
Alert management endpoints.

POST /alerts/generate           — score all accounts and persist alerts above threshold.
GET  /alerts                    — list alerts (filterable by severity / status).
PATCH /alerts/{alert_id}        — update an alert's status.

TODO (sync-point): swap _MOCK_CSV for the real /features endpoint output
once the data-pipeline team delivers it.
"""

from __future__ import annotations

import logging
import pathlib
from typing import Literal, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, field_validator

from app.services.alert_generator import (
    VALID_STATUSES,
    generate_alerts,
    get_alerts,
    update_alert_status,
)
from app.services.risk_scorer import score_accounts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])

# ---------------------------------------------------------------------------
# Data source
# ---------------------------------------------------------------------------
_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"

# TODO (sync-point): replace with the real pipeline output path / call.
_MOCK_CSV = _DATA_DIR / "mock_features.csv"


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class AlertStatusUpdate(BaseModel):
    status: Literal["OPEN", "REVIEWED", "DISMISSED"]

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
        return v


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_feature_df() -> pd.DataFrame:
    if not _MOCK_CSV.exists():
        raise HTTPException(
            status_code=422,
            detail=(
                f"Feature CSV not found at '{_MOCK_CSV}'. "
                "Run scripts/generate_mock_features.py first."
            ),
        )
    return pd.read_csv(_MOCK_CSV)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/generate",
    summary="Score all accounts and generate alerts for high-risk ones",
    response_description="List of alerts generated / updated in this run.",
)
def trigger_alert_generation(
    threshold: float = Query(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum risk_score to trigger an alert.",
    ),
) -> dict:
    """
    1. Load the feature matrix.
    2. Score every account via the trained model.
    3. Persist alerts for all accounts whose `risk_score > threshold` into SQLite.

    Alerts are **upserted**: re-running does not reset REVIEWED/DISMISSED
    statuses — only the score/severity/summary are refreshed.

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

    try:
        alerts = generate_alerts(scored, threshold=threshold)
    except Exception as exc:
        logger.exception("generate_alerts failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Alert generation failed: {exc}") from exc

    return {
        "generated": len(alerts),
        "threshold": threshold,
        "alerts": alerts,
    }


@router.get(
    "",
    summary="List alerts",
    response_description="Alerts filtered by severity and/or status, sorted by risk_score desc.",
)
def list_alerts(
    severity: Optional[str] = Query(
        default=None,
        description="Filter by severity: 'High' or 'Critical'.",
    ),
    status: Optional[str] = Query(
        default=None,
        description="Filter by status: 'OPEN', 'REVIEWED', or 'DISMISSED'.",
    ),
) -> dict:
    """
    Return persisted alerts from SQLite.

    - **severity**: `High` | `Critical`
    - **status**: `OPEN` | `REVIEWED` | `DISMISSED`

    All filters are combinable.  Omit to return all alerts.
    """
    # Validate query params
    if severity is not None and severity not in ("High", "Critical"):
        raise HTTPException(
            status_code=422,
            detail="severity must be 'High' or 'Critical'",
        )
    if status is not None and status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of: {', '.join(sorted(VALID_STATUSES))}",
        )

    try:
        alerts = get_alerts(severity=severity, status=status)
    except Exception as exc:
        logger.exception("get_alerts failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve alerts: {exc}") from exc

    return {
        "count": len(alerts),
        "filters": {"severity": severity, "status": status},
        "alerts": alerts,
    }


@router.patch(
    "/{alert_id}",
    summary="Update an alert's status",
    response_description="The updated alert record.",
)
def patch_alert(alert_id: str, body: AlertStatusUpdate) -> dict:
    """
    Transition an alert to a new status.

    - **OPEN** → the default state when an alert is first created.
    - **REVIEWED** → an analyst has reviewed the alert.
    - **DISMISSED** → the alert was assessed as a false positive.

    The change is persisted to SQLite and survives a server restart.
    """
    try:
        updated = update_alert_status(alert_id, body.status)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"alert_id '{alert_id}' not found.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("update_alert_status failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Update failed: {exc}") from exc

    return updated
