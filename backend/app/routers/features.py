"""
app/routers/features.py
------------------------
GET /features  — run the full feature pipeline on the uploaded dataset
                 and return the feature matrix as a JSON list of records.

Schema validation
-----------------
Before returning, the endpoint performs a programmatic diff between
the response keys and the agreed schema columns.  Any mismatch is
reported in the response body and logged so Track B catches drift early.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.services.feature_pipeline import SCHEMA_COLUMNS, build_feature_matrix

router = APIRouter(prefix="/features", tags=["features"])

_TRANSACTIONS_PATH = Path(__file__).resolve().parent.parent / "data" / "transactions.csv"

# The 22 non-label feature columns Track B expects (label is optional)
_EXPECTED_FEATURE_KEYS: list[str] = SCHEMA_COLUMNS  # account_id + 21 features


@router.get(
    "",
    summary="Run feature pipeline and return feature matrix",
    response_description=(
        "List of per-account feature records.  "
        "Keys match docs/feature_schema.md exactly."
    ),
)
def get_features() -> JSONResponse:
    """
    Run the full feature pipeline on the previously uploaded transaction CSV
    (``app/data/transactions.csv``) and return one record per account.

    Performs a live schema diff to catch column name drift.

    Raises HTTP 404 if no dataset has been uploaded yet.
    Raises HTTP 500 if the pipeline fails or a schema mismatch is detected.
    """
    if not _TRANSACTIONS_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "No transaction dataset found.  "
                "Upload one first via POST /upload-dataset."
            ),
        )

    # ---- run pipeline ----
    try:
        df = build_feature_matrix(_TRANSACTIONS_PATH)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Feature pipeline failed: {exc}",
        ) from exc

    # ---- schema diff (AC1) ----
    response_keys  = list(df.columns)
    missing_keys   = [k for k in _EXPECTED_FEATURE_KEYS if k not in response_keys]
    extra_keys     = [
        k for k in response_keys
        if k not in _EXPECTED_FEATURE_KEYS and k != "is_mule_pattern"
    ]

    schema_ok = not missing_keys and not extra_keys

    if not schema_ok:
        raise HTTPException(
            status_code=500,
            detail={
                "error":        "Schema mismatch detected",
                "missing_keys": missing_keys,
                "extra_keys":   extra_keys,
            },
        )

    # ---- null check (AC2) ----
    null_counts = df.isnull().sum()
    null_cols   = null_counts[null_counts > 0].to_dict()
    if null_cols:
        raise HTTPException(
            status_code=500,
            detail={
                "error":           "NaN values detected in feature matrix",
                "affected_columns": null_cols,
            },
        )

    # ---- serialise ----
    # Replace inf/-inf (can appear in rare zscore edge cases)
    import numpy as np
    df = df.replace([np.inf, -np.inf], 0.0)

    records = df.to_dict(orient="records")

    return JSONResponse(
        content={
            "account_count": len(records),
            "column_count":  len(df.columns),
            "schema_diff": {
                "ok":          schema_ok,
                "missing":     missing_keys,
                "extra":       extra_keys,
            },
            "records": records,
        }
    )
