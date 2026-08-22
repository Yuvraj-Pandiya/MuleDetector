"""
app/routers/train.py
=====================
POST /train  — triggers model training on the mock feature CSV.

TODO (sync-point): swap the CSV source below for the real /features
endpoint output once the data-pipeline team delivers it.  The call to
train_model() does not change; only the DataFrame source changes.
"""

from __future__ import annotations

import logging
import pathlib

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.services.feature_pipeline import build_feature_matrix

from app.services.model_trainer import METRICS_PATH, MODEL_PATH, train_model

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/train", tags=["training"])

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"

# TODO (sync-point): replace this path with the real pipeline output.
_TRANSACTIONS_CSV = _DATA_DIR / "transactions.csv"


# ---------------------------------------------------------------------------
# Response helpers
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

@router.post(
    "",
    summary="Train mule-detection model",
    response_description="Training metrics (precision, recall, F1, ROC-AUC, etc.)",
)
def trigger_training() -> dict:
    """
    Load the feature matrix CSV and train the mule-detection model.

    - Uses XGBoost when the `is_mule_pattern` label column is present and
      has both classes.
    - Falls back to IsolationForest otherwise (`"unsupervised": true` in
      the response).

    Artefacts written:
    - `app/data/model.pkl`    — trained model (joblib)
    - `app/data/metrics.json` — evaluation metrics (JSON)

    Returns the metrics dict directly so callers can inspect results
    without a separate round-trip.
    """
    logger.info("POST /train received — generating features from %s", _TRANSACTIONS_CSV)

    df = _load_feature_df()

    logger.info("Feature CSV loaded: %d rows × %d cols", len(df), len(df.columns))

    try:
        metrics = train_model(df)
    except Exception as exc:
        logger.exception("Training failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Training failed: {exc}") from exc

    logger.info(
        "Training complete — model: %s  artefacts: model.pkl=%s  metrics.json=%s",
        metrics.get("model_type"),
        MODEL_PATH.exists(),
        METRICS_PATH.exists(),
    )

    return {
        "status": "ok",
        "artefacts": {
            "model": str(MODEL_PATH),
            "metrics": str(METRICS_PATH),
        },
        "metrics": metrics,
    }
