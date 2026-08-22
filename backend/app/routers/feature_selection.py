"""
app/routers/feature_selection.py
==================================
FastAPI router for the Feature Selection & Ranking pipeline.

Endpoints
---------
POST  /feature-selection/run        Run full 6-method pipeline on current data
GET   /feature-selection/ranking    Return feature_ranking.csv contents as JSON
GET   /feature-selection/top-features?n=10  Return top N features (default 10)
GET   /feature-selection/report     Return full feature_selection_report.json
GET   /feature-selection/plot       Stream feature_importance_plot.png
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

import pandas as pd

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feature-selection", tags=["Feature Selection"])

_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_mock_features() -> pd.DataFrame:
    """Load mock_features.csv (or generate if absent) as the feature DataFrame."""
    mock_path = _DATA_DIR / "mock_features.csv"
    if not mock_path.exists():
        try:
            from app.services.mock_generator import generate_mock_features_csv
            generate_mock_features_csv(mock_path)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Could not load or generate mock features: {exc}",
            )
    return pd.read_csv(mock_path)


def _load_real_features() -> Optional[pd.DataFrame]:
    """Try to load features.csv (from upload) if present."""
    features_path = _DATA_DIR / "features.csv"
    if features_path.exists():
        try:
            return pd.read_csv(features_path)
        except Exception:
            pass
    return None


def _get_feature_df() -> pd.DataFrame:
    """Return best available feature DataFrame (real > mock)."""
    real = _load_real_features()
    if real is not None and len(real) > 0:
        return real
    return _load_mock_features()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/run", response_class=JSONResponse)
async def run_feature_selection() -> Dict[str, Any]:
    """
    Run the full 6-method feature selection and ranking pipeline.

    Uses real uploaded features.csv if present, otherwise falls back to mock data.
    Generates and saves all 5 artifacts to app/data/.

    Returns
    -------
    dict
        Pipeline summary including top-3 features, retention counts, elapsed time,
        and artifact paths.
    """
    try:
        from app.services.feature_selector import FeatureSelector
        feature_df = _get_feature_df()
        selector = FeatureSelector(data_dir=_DATA_DIR)
        summary = selector.run(feature_df, label_col="is_mule_pattern")
        return summary
    except Exception as exc:
        logger.exception("[/feature-selection/run] Pipeline failed")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/ranking", response_class=JSONResponse)
async def get_feature_ranking() -> List[Dict[str, Any]]:
    """
    Return the contents of feature_ranking.csv as a JSON list.

    Each element contains: composite_rank, feature_name, feature_group,
    composite_score, retention_decision, method, all individual method scores
    and per-method ranks, and interpretation string.

    Raises 404 if the pipeline has not been run yet.
    """
    csv_path = _DATA_DIR / "feature_ranking.csv"
    if not csv_path.exists():
        raise HTTPException(
            status_code=404,
            detail="feature_ranking.csv not found. Run POST /feature-selection/run first.",
        )
    try:
        df = pd.read_csv(csv_path)
        return df.to_dict(orient="records")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not read feature_ranking.csv: {exc}")


@router.get("/top-features", response_class=JSONResponse)
async def get_top_features(
    n: int = Query(default=10, ge=1, le=50, description="Number of top features to return (1-50)"),
) -> List[Dict[str, Any]]:
    """
    Return the top N features from the feature ranking.

    Query parameter:
      n (int): Number of features to return. Default 10, max 50.

    Each feature entry includes: rank, feature_name, feature_group, importance,
    composite_score, method, interpretation, retention_decision, all method scores, all ranks.

    Raises 404 if the pipeline has not been run yet.
    """
    # Try top_10 / top_20 cached JSON first for common requests
    if n == 10:
        cached = _DATA_DIR / "top_10_features.json"
        if cached.exists():
            try:
                return json.loads(cached.read_text(encoding="utf-8"))
            except Exception:
                pass
    if n == 20:
        cached = _DATA_DIR / "top_20_features.json"
        if cached.exists():
            try:
                return json.loads(cached.read_text(encoding="utf-8"))
            except Exception:
                pass

    # Fallback: read from CSV
    csv_path = _DATA_DIR / "feature_ranking.csv"
    if not csv_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Feature ranking not found. Run POST /feature-selection/run first.",
        )
    try:
        df = pd.read_csv(csv_path).head(n)
        return df.to_dict(orient="records")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/report", response_class=JSONResponse)
async def get_feature_selection_report() -> Dict[str, Any]:
    """
    Return the full feature_selection_report.json.

    Contains: pipeline metadata, rejection policy, summary statistics,
    per-group counts, top_10, top_20, and the complete all_features list
    with scores and interpretations for every evaluated feature.

    Raises 404 if the pipeline has not been run yet.
    """
    report_path = _DATA_DIR / "feature_selection_report.json"
    if not report_path.exists():
        raise HTTPException(
            status_code=404,
            detail="feature_selection_report.json not found. Run POST /feature-selection/run first.",
        )
    try:
        return json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not read report: {exc}")


@router.get("/plot")
async def get_feature_importance_plot() -> FileResponse:
    """
    Stream feature_importance_plot.png as an image response.

    Returns a 4-panel dark-theme horizontal bar chart comparing XGBoost gain,
    SHAP global importance, mutual information, and Mann-Whitney effect size
    for the top 30 ranked features. RETAINED features are shown in colour,
    REJECTED features in red.

    Raises 404 if the pipeline has not been run yet.
    """
    plot_path = _DATA_DIR / "feature_importance_plot.png"
    if not plot_path.exists():
        raise HTTPException(
            status_code=404,
            detail="feature_importance_plot.png not found. Run POST /feature-selection/run first.",
        )
    return FileResponse(
        path=str(plot_path),
        media_type="image/png",
        filename="feature_importance_plot.png",
    )
