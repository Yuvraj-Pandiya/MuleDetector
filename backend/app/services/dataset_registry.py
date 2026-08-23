"""
app/services/dataset_registry.py
================================
Multi-Dataset Management & Active Dataset Switcher Registry.

Features:
- Maintains list of registered datasets (PaySim Benchmark 15,420 accounts + user CSV uploads).
- Manages persistent active dataset state via JSON metadata store.
- Provides unified `get_active_feature_df()` for routers (dashboard, predict, train, sar, etc.).
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_REGISTRY_JSON = _DATA_DIR / "dataset_registry.json"
_ACTIVE_MARKER = _DATA_DIR / "active_upload.json"
_MOCK_CSV = _DATA_DIR / "mock_features.csv"
_TRANSACTIONS_CSV = _DATA_DIR / "transactions.csv"
_UPLOADS_DIR = _DATA_DIR / "uploads"

PAYSIM_BENCHMARK_ID = "paysim_benchmark"

PAYSIM_BENCHMARK_META: Dict[str, Any] = {
    "id": PAYSIM_BENCHMARK_ID,
    "name": "PaySim Benchmark (15,420 accounts)",
    "type": "benchmark",
    "description": "Standardized FinTech AML synthetic benchmark with 15,420 accounts and 185,040 transactions.",
    "row_count": 185040,
    "account_count": 15420,
    "created_at": "2026-08-20T00:00:00Z",
    "is_builtin": True,
    "is_active": True,
}


def _ensure_data_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _load_registry_data() -> Dict[str, Any]:
    _ensure_data_dir()
    if not _REGISTRY_JSON.exists():
        initial = {
            "active_dataset_id": PAYSIM_BENCHMARK_ID,
            "datasets": {
                PAYSIM_BENCHMARK_ID: PAYSIM_BENCHMARK_META.copy(),
            },
        }
        _save_registry_data(initial)
        return initial

    try:
        with _REGISTRY_JSON.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if PAYSIM_BENCHMARK_ID not in data.get("datasets", {}):
                data.setdefault("datasets", {})[PAYSIM_BENCHMARK_ID] = PAYSIM_BENCHMARK_META.copy()
            if "active_dataset_id" not in data or data["active_dataset_id"] not in data["datasets"]:
                data["active_dataset_id"] = PAYSIM_BENCHMARK_ID
            return data
    except Exception as exc:
        logger.warning("Failed reading dataset_registry.json, resetting: %s", exc)
        initial = {
            "active_dataset_id": PAYSIM_BENCHMARK_ID,
            "datasets": {
                PAYSIM_BENCHMARK_ID: PAYSIM_BENCHMARK_META.copy(),
            },
        }
        _save_registry_data(initial)
        return initial


def _save_registry_data(data: Dict[str, Any]) -> None:
    _ensure_data_dir()
    tmp = _REGISTRY_JSON.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(_REGISTRY_JSON)


def list_datasets() -> List[Dict[str, Any]]:
    """Return all available datasets with their active status."""
    reg = _load_registry_data()
    active_id = reg.get("active_dataset_id", PAYSIM_BENCHMARK_ID)
    result = []
    for d_id, meta in reg.get("datasets", {}).items():
        entry = dict(meta)
        entry["is_active"] = (d_id == active_id)
        result.append(entry)
    # Sort with benchmark first, then newest custom uploads
    result.sort(key=lambda x: (not x.get("is_builtin", False), x.get("created_at", "")), reverse=True)
    # Put benchmark at top
    result.sort(key=lambda x: not x.get("is_builtin", False))
    return result


def get_active_dataset() -> Dict[str, Any]:
    """Return metadata of the currently active dataset."""
    reg = _load_registry_data()
    active_id = reg.get("active_dataset_id", PAYSIM_BENCHMARK_ID)
    datasets = reg.get("datasets", {})
    if active_id in datasets:
        meta = dict(datasets[active_id])
        meta["is_active"] = True
        return meta
    return dict(PAYSIM_BENCHMARK_META)


def set_active_dataset(dataset_id: str) -> Dict[str, Any]:
    """
    Switch active dataset.
    If 'paysim_benchmark', deletes active_upload.json marker so system uses mock benchmark.
    If custom upload, points active_upload.json to that dataset's CSV.
    """
    reg = _load_registry_data()
    if dataset_id not in reg.get("datasets", {}):
        raise ValueError(f"Dataset '{dataset_id}' not found in registry.")

    reg["active_dataset_id"] = dataset_id
    _save_registry_data(reg)

    if dataset_id == PAYSIM_BENCHMARK_ID:
        if _ACTIVE_MARKER.exists():
            try:
                _ACTIVE_MARKER.unlink()
            except Exception as e:
                logger.warning("Could not unlink active_upload.json: %s", e)
        logger.info("[DatasetRegistry] Switched active dataset to '%s'", PAYSIM_BENCHMARK_ID)
    else:
        meta = reg["datasets"][dataset_id]
        csv_path = meta.get("file_path", "")
        marker_data = {
            "dataset_id": dataset_id,
            "name": meta.get("name", "Custom Upload"),
            "file_path": csv_path,
            "activated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        with _ACTIVE_MARKER.open("w", encoding="utf-8") as f:
            json.dump(marker_data, f, indent=2)
        logger.info("[DatasetRegistry] Switched active dataset to custom upload '%s' (%s)", dataset_id, meta.get("name"))

    return get_active_dataset()


def register_upload_dataset(
    dataset_id: str,
    name: str,
    file_path: str,
    row_count: int,
    account_count: int,
    quality_report: Optional[Dict[str, Any]] = None,
    set_as_active: bool = True,
) -> Dict[str, Any]:
    """Register a new processed CSV dataset in the registry."""
    reg = _load_registry_data()
    meta = {
        "id": dataset_id,
        "name": name or f"Upload {dataset_id}",
        "type": "custom_upload",
        "description": f"User uploaded AML dataset with {row_count} transactions across {account_count} accounts.",
        "row_count": row_count,
        "account_count": account_count,
        "file_path": str(file_path),
        "quality_report": quality_report or {},
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "is_builtin": False,
    }
    reg.setdefault("datasets", {})[dataset_id] = meta
    if set_as_active:
        reg["active_dataset_id"] = dataset_id
    _save_registry_data(reg)

    if set_as_active:
        set_active_dataset(dataset_id)

    return meta


def delete_upload_dataset(dataset_id: str) -> bool:
    """Delete a user uploaded dataset from registry and disk."""
    if dataset_id == PAYSIM_BENCHMARK_ID:
        raise ValueError("Cannot delete built-in PaySim benchmark dataset.")

    reg = _load_registry_data()
    if dataset_id not in reg.get("datasets", {}):
        return False

    meta = reg["datasets"].pop(dataset_id)
    # Remove file from disk if present
    file_path = meta.get("file_path")
    if file_path:
        p = Path(file_path)
        if p.exists():
            try:
                p.unlink()
            except Exception as e:
                logger.warning("Could not delete dataset file %s: %s", p, e)

    # If deleted dataset was active, fallback to benchmark
    if reg.get("active_dataset_id") == dataset_id:
        reg["active_dataset_id"] = PAYSIM_BENCHMARK_ID
        if _ACTIVE_MARKER.exists():
            _ACTIVE_MARKER.unlink(missing_ok=True)

    _save_registry_data(reg)
    logger.info("[DatasetRegistry] Deleted dataset '%s'", dataset_id)
    return True


def rename_dataset(dataset_id: str, new_name: str) -> Dict[str, Any]:
    """Rename an existing dataset."""
    if dataset_id == PAYSIM_BENCHMARK_ID:
        raise ValueError("Cannot rename built-in PaySim benchmark dataset.")
    reg = _load_registry_data()
    if dataset_id not in reg.get("datasets", {}):
        raise ValueError(f"Dataset '{dataset_id}' not found.")
    reg["datasets"][dataset_id]["name"] = new_name.strip()
    _save_registry_data(reg)
    return reg["datasets"][dataset_id]


def get_active_feature_df() -> Tuple[pd.DataFrame, bool]:
    """
    Unified feature loader:
    Returns (DataFrame, is_benchmark: bool).
    If active dataset is PaySim Benchmark -> returns mock_features.csv (15,420 scale).
    If active dataset is custom upload -> returns feature matrix built from that upload's transactions CSV.
    """
    active = get_active_dataset()
    if active.get("id") != PAYSIM_BENCHMARK_ID:
        csv_path_str = active.get("file_path")
        if csv_path_str:
            csv_path = Path(csv_path_str)
            if csv_path.exists() and csv_path.stat().st_size > 100:
                try:
                    from app.services.feature_pipeline import build_feature_matrix
                    df = build_feature_matrix(csv_path)
                    if len(df) > 0:
                        return df, False
                except Exception as exc:
                    logger.warning("Failed building feature matrix for %s, fallback to benchmark: %s", csv_path, exc)

    # Fallback to PaySim Benchmark
    if not _MOCK_CSV.exists():
        from app.services.mock_generator import generate_mock_features_csv
        generate_mock_features_csv(_MOCK_CSV)
    return pd.read_csv(_MOCK_CSV), True
