from typing import List
"""
app/routers/upload.py
---------------------
POST /upload-dataset  — accept a CSV upload, persist it, validate it.
"""
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from app.services.data_loader import load_transactions

router = APIRouter(prefix="/upload-dataset", tags=["data"])

# Where the uploaded dataset is persisted on disk
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_TRANSACTIONS_PATH = _DATA_DIR / "transactions.csv"


@router.post(
    "",
    summary="Upload transaction CSV dataset",
    response_description="Row count and column list of the accepted CSV.",
)
async def upload_dataset(file: UploadFile = File(..., description="Transaction CSV file")):
    """
    Upload a CSV file containing raw transactions.

    - Saves the file to ``app/data/transactions.csv``.
    - Validates that all required columns are present.
    - Returns ``{row_count, columns}`` on success.
    - Returns HTTP 400 with details if validation fails.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=422,
            detail="Only .csv files are accepted.",
        )

    # Persist the upload
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with _TRANSACTIONS_PATH.open("wb") as out:
            shutil.copyfileobj(file.file, out)
    finally:
        await file.close()

    # Validate & parse
    try:
        df = load_transactions(_TRANSACTIONS_PATH)
    except ValueError as exc:
        # Remove the invalid file so it can't be used downstream
        _TRANSACTIONS_PATH.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        _TRANSACTIONS_PATH.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500, detail=f"Unexpected error while reading CSV: {exc}"
        ) from exc

    return JSONResponse(
        status_code=200,
        content={
            "row_count": len(df),
            "columns": list(df.columns),
        },
    )
