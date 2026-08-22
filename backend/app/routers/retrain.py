"""
app/routers/retrain.py
======================
Endpoints for controlled Human-in-the-Loop (HITL) feedback collection,
candidate dataset construction, candidate model training, model comparison,
and approved model promotion.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.services.candidate_trainer import (
    compare_candidate_vs_production,
    get_feedback_summary,
    promote_candidate_model,
    train_candidate_model,
    validate_and_build_candidate_dataset,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/retrain", tags=["retraining"])


@router.get("/feedback-summary", summary="Get summary of collected feedback entries and validated labels")
def fetch_feedback_summary() -> Dict[str, Any]:
    """Return counts of CONFIRMED_MULE, LEGITIMATE, FALSE_POSITIVE, and UNDER_INVESTIGATION decisions."""
    return get_feedback_summary()


@router.post("/candidate", summary="Collect feedback, validate labels, build candidate dataset and train candidate model")
def trigger_candidate_training() -> Dict[str, Any]:
    """
    Collect feedback records, validate labels:
      - CONFIRMED_MULE -> target label 1
      - LEGITIMATE / FALSE_POSITIVE -> target label 0
      - UNDER_INVESTIGATION -> pending/skipped

    Trains candidate XGBoost classifier and persists candidate_model.pkl and candidate_metrics.json.
    DOES NOT automatically retrain or overwrite the production model.
    """
    try:
        metrics = train_candidate_model()
        comparison = compare_candidate_vs_production()
        return {
            "status": "candidate_trained",
            "candidate_metrics": metrics,
            "comparison": comparison,
        }
    except Exception as exc:
        logger.exception("Candidate retraining failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Candidate training failed: {exc}") from exc


@router.get("/compare", summary="Compare candidate model metrics vs production model metrics")
def get_candidate_comparison() -> Dict[str, Any]:
    """Return side-by-side metric comparison and promotion recommendation."""
    try:
        return compare_candidate_vs_production()
    except Exception as exc:
        logger.exception("Failed to compare candidate vs production model: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/promote", summary="Human-in-the-loop approval: promote candidate model to production")
def trigger_model_promotion() -> Dict[str, Any]:
    """
    Human administrator approval action:
    Promotes candidate_model.pkl -> model.pkl and updates production model version tag.
    """
    try:
        res = promote_candidate_model()
        return res
    except Exception as exc:
        logger.exception("Model promotion failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Model promotion failed: {exc}") from exc
