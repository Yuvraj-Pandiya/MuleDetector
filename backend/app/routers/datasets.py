"""
app/routers/datasets.py
=======================
Endpoints for Multi-Dataset Management and Switching.

Endpoints:
  GET    /datasets                 — List all registered datasets with active indicator
  GET    /datasets/active          — Get current active dataset metadata
  POST   /datasets/{id}/activate   — Switch active dataset to specified ID
  DELETE /datasets/{id}            — Delete a custom dataset
  POST   /datasets/{id}/rename     — Rename a custom dataset
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.services.dataset_registry import (
    delete_upload_dataset,
    get_active_dataset,
    list_datasets,
    rename_dataset,
    set_active_dataset,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datasets", tags=["datasets"])


class RenameDatasetPayload(BaseModel):
    name: str


@router.get(
    "",
    summary="List all available datasets",
    response_description="List of registered datasets with active indicator.",
)
def get_all_datasets() -> Dict[str, Any]:
    """Return all available datasets in the registry."""
    datasets = list_datasets()
    active = get_active_dataset()
    return {
        "datasets": datasets,
        "active_dataset_id": active.get("id"),
        "active_dataset": active,
        "total_count": len(datasets),
    }


@router.get(
    "/active",
    summary="Get active dataset metadata",
    response_description="Metadata of the currently active dataset.",
)
def get_current_active_dataset() -> Dict[str, Any]:
    """Return the currently active dataset metadata."""
    return get_active_dataset()


@router.post(
    "/{dataset_id}/activate",
    summary="Switch active dataset",
    response_description="Updated active dataset metadata.",
)
def activate_dataset_endpoint(dataset_id: str) -> Dict[str, Any]:
    """Switch active dataset by ID."""
    try:
        active = set_active_dataset(dataset_id)
        return {
            "status": "success",
            "message": f"Active dataset switched to '{active.get('name')}'",
            "active_dataset": active,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed activating dataset %s: %s", dataset_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to activate dataset: {exc}") from exc


@router.delete(
    "/{dataset_id}",
    summary="Delete a custom dataset",
    response_description="Deletion status.",
)
def delete_dataset_endpoint(dataset_id: str) -> Dict[str, Any]:
    """Delete a user uploaded dataset."""
    try:
        success = delete_upload_dataset(dataset_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")
        active = get_active_dataset()
        return {
            "status": "success",
            "deleted_id": dataset_id,
            "active_dataset": active,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed deleting dataset %s: %s", dataset_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to delete dataset: {exc}") from exc


@router.post(
    "/{dataset_id}/rename",
    summary="Rename a custom dataset",
    response_description="Updated dataset metadata.",
)
def rename_dataset_endpoint(dataset_id: str, payload: RenameDatasetPayload) -> Dict[str, Any]:
    """Rename a custom dataset."""
    if not payload.name or not payload.name.strip():
        raise HTTPException(status_code=422, detail="Dataset name cannot be empty.")
    try:
        updated = rename_dataset(dataset_id, payload.name.strip())
        return {
            "status": "success",
            "dataset": updated,
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to rename dataset: {exc}") from exc
