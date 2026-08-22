"""
app/routers/feedback.py
========================
Endpoints for submitting and retrieving investigator feedback and audit trails.
"""

from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, field_validator

from app.services.feedback_store import (
    VALID_DECISIONS,
    get_feedback_history,
    submit_feedback,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackSubmission(BaseModel):
    alert_id: str
    account_id: str
    decision: Literal["CONFIRMED_MULE", "LEGITIMATE", "FALSE_POSITIVE", "UNDER_INVESTIGATION"]
    note: str
    investigator: Optional[str] = "Analyst #402"

    @field_validator("decision")
    @classmethod
    def decision_must_be_valid(cls, v: str) -> str:
        if v not in VALID_DECISIONS:
            raise ValueError(f"decision must be one of {sorted(VALID_DECISIONS)}")
        return v


@router.post("", summary="Submit investigator feedback decision and note")
def create_feedback(body: FeedbackSubmission) -> dict:
    """
    Record an investigator's compliance decision and note.
    Transitions alert status and logs audit trail.
    """
    try:
        res = submit_feedback(
            alert_id=body.alert_id,
            account_id=body.account_id,
            decision=body.decision,
            note=body.note,
            investigator=body.investigator or "Analyst #402",
        )
        return res
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to submit feedback: %s", exc)
        raise HTTPException(status_code=500, detail=f"Submission failed: {exc}") from exc


@router.get("", summary="Get previous investigator decisions and audit log")
def list_feedback(
    account_id: Optional[str] = Query(None, description="Account ID"),
    alert_id: Optional[str] = Query(None, description="Alert ID"),
) -> dict:
    """
    Fetch history of investigator decisions, notes, timestamps, and analysts.
    """
    history = get_feedback_history(account_id=account_id, alert_id=alert_id)
    current_status = history[0]["decision"] if history else "NONE"
    return {
        "account_id": account_id,
        "alert_id": alert_id,
        "current_status": current_status,
        "history": history,
        "total": len(history),
    }
