"""
app/routers/upload.py
---------------------
Universal CSV Ingestion and Schema Normalization Endpoints.

Endpoints:
  POST /upload-dataset           — Direct CSV upload (Backward compatible).
  POST /upload-dataset/preview   — Profile CSV, return column mapping & confidence scores.
  POST /upload-dataset/confirm   — Confirm user mapping, normalize, and activate dataset.
  GET  /upload-dataset/template  — Download Canonical AML CSV Template.
"""

import shutil
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from app.services.schema import (
    map_columns,
    normalize_and_save_dataset,
    profile_csv,
)

router = APIRouter(prefix="/upload-dataset", tags=["data"])

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_UPLOADS_DIR = _DATA_DIR / "uploads"
_TRANSACTIONS_PATH = _DATA_DIR / "transactions.csv"


class ConfirmMappingPayload(BaseModel):
    upload_id: str
    mapping: Dict[str, str]
    dataset_name: Optional[str] = None


@router.get(
    "/template",
    summary="Download Canonical AML CSV Template",
    response_description="CSV template with standard canonical headers.",
)
def download_canonical_template():
    """Return a standard Canonical AML CSV template as downloadable text/csv."""
    headers = [
        "transaction_id",
        "sender_account_id",
        "receiver_account_id",
        "amount",
        "timestamp",
        "transaction_type",
        "is_mule_pattern",
    ]
    sample_row = [
        "TXN_00000001",
        "ACC-001005",
        "ACC-002012",
        "25000.00",
        "2026-08-23T10:30:00Z",
        "TRANSFER",
        "1",
    ]
    csv_content = ",".join(headers) + "\n" + ",".join(sample_row) + "\n"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=canonical_aml_template.csv"},
    )


@router.post(
    "/preview",
    summary="Profile CSV and preview schema mapping candidates",
    response_description="Column profiles, mapped fields, confidence scores, and capability flags.",
)
async def preview_upload_dataset(file: UploadFile = File(..., description="Transaction CSV file")):
    """
    Profile raw CSV file and return multi-stage column mapping predictions with confidence scores.
    Does NOT modify active ML dataset.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Only .csv files are accepted.")

    _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    upload_id = f"up_{uuid.uuid4().hex[:8]}"
    raw_save_path = _UPLOADS_DIR / f"{upload_id}.csv"

    try:
        with raw_save_path.open("wb") as out:
            shutil.copyfileobj(file.file, out)
    finally:
        await file.close()

    try:
        prof_res = profile_csv(raw_save_path)
        map_res = map_columns(prof_res["column_profiles"])
    except Exception as exc:
        raw_save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Failed to profile CSV: {exc}") from exc

    user_msg = ""
    if map_res.status == "dataset_not_applicable":
        user_msg = f"Dataset Not Applicable: The uploaded file is missing mandatory AML transaction fields: {', '.join(map_res.missing_required)}. Please select columns for those fields or upload a valid transaction log."

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder({
            "upload_id": upload_id,
            "status": map_res.status,
            "user_message": user_msg,
            "total_rows_estimated": prof_res["total_rows_estimated"],
            "raw_headers": prof_res["raw_headers"],
            "columns": [
                {
                    "source": m.source,
                    "target": m.target,
                    "confidence": m.confidence,
                    "status": m.status,
                    "matched_stage": m.matched_stage,
                    "inferred_type": m.inferred_type,
                    "sample_values": m.sample_values,
                    "candidate_targets": m.candidate_targets,
                }
                for m in map_res.mappings
            ],
            "mapped_dict": map_res.mapped_dict,
            "missing_required": map_res.missing_required,
            "unmapped_columns": map_res.unmapped_columns,
            "can_train": map_res.can_train,
            "can_predict": map_res.can_predict,
        }),
    )


@router.post(
    "/confirm",
    summary="Confirm column mapping, normalize CSV, and activate dataset",
    response_description="Normalized row count, columns, and data quality report.",
)
def confirm_upload_mapping(payload: ConfirmMappingPayload):
    """
    Accept user-confirmed mapping, transform dataset into Canonical Schema,
    save normalized copy, and activate as current dataset for ML pipelines.
    """
    _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    raw_save_path = _UPLOADS_DIR / f"{payload.upload_id}.csv"

    if not raw_save_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Upload session '{payload.upload_id}' not found or expired. Please upload file again.",
        )

    try:
        norm_res = normalize_and_save_dataset(
            raw_csv_path=raw_save_path,
            mapping_dict=payload.mapping,
            upload_id=payload.upload_id,
        )
        
        # Register into Named Dataset Registry
        from app.services.dataset_registry import register_upload_dataset
        import pandas as pd
        
        norm_csv_path = norm_res.get("normalized_csv_path")
        account_cnt = 0
        if norm_csv_path and Path(norm_csv_path).exists():
            try:
                df_temp = pd.read_csv(norm_csv_path)
                account_cnt = len(set(df_temp.get("sender_account_id", [])).union(set(df_temp.get("receiver_account_id", []))))
            except Exception:
                account_cnt = norm_res.get("row_count", 0)
        
        ds_name = payload.dataset_name.strip() if payload.dataset_name and payload.dataset_name.strip() else f"Uploaded Dataset ({payload.upload_id})"
        registered_ds = register_upload_dataset(
            dataset_id=payload.upload_id,
            name=ds_name,
            file_path=norm_csv_path or str(_TRANSACTIONS_PATH),
            row_count=norm_res["row_count"],
            account_count=account_cnt,
            quality_report=norm_res["quality_report"],
            set_as_active=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to normalize dataset: {exc}") from exc

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder({
            "status": "success",
            "upload_id": norm_res["upload_id"],
            "row_count": norm_res["row_count"],
            "columns": norm_res["columns"],
            "quality_report": norm_res["quality_report"],
            "dataset": registered_ds,
        }),
    )


@router.post(
    "",
    summary="Upload transaction CSV dataset (Backward Compatible Direct Upload)",
    response_description="Row count and column list of accepted canonical/auto-mapped CSV.",
)
async def upload_dataset(file: UploadFile = File(..., description="Transaction CSV file")):
    """
    Direct upload endpoint maintaining 100% backward compatibility.
    Saves raw file, profiles/auto-maps headers, normalizes into canonical schema,
    and updates active transactions.csv dataset.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Only .csv files are accepted.")

    _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    upload_id = f"up_{uuid.uuid4().hex[:8]}"
    raw_save_path = _UPLOADS_DIR / f"{upload_id}.csv"

    try:
        with raw_save_path.open("wb") as out:
            shutil.copyfileobj(file.file, out)
    finally:
        await file.close()

    try:
        prof_res = profile_csv(raw_save_path)
        map_res = map_columns(prof_res["column_profiles"])

        if map_res.missing_required:
            raise ValueError(
                f"Missing required canonical field(s): {', '.join(map_res.missing_required)}. Found headers: {prof_res['raw_headers']}"
            )

        norm_res = normalize_and_save_dataset(
            raw_csv_path=raw_save_path,
            mapping_dict=map_res.mapped_dict,
            upload_id=upload_id,
        )
    except ValueError as exc:
        raw_save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raw_save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error processing CSV: {exc}") from exc

    return JSONResponse(
        status_code=200,
        content={
            "row_count": norm_res["row_count"],
            "columns": norm_res["columns"],
            "quality_report": norm_res["quality_report"],
        },
    )
