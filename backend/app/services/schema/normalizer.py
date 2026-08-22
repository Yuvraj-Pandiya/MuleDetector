"""
app/services/schema/normalizer.py
==================================
Dataset Normalizer Service & Storage Manager.

Maintains strict separation:
  - Original Upload: app/data/uploads/<upload_id>.csv  (UNTOUCHED)
  - Normalized Output: app/data/normalized/<upload_id>_normalized.csv
  - Active Compatibility Link: app/data/transactions.csv  (FOR DOWNSTREAM CONSUMERS)
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Union, Tuple

import numpy as np
import pandas as pd

from app.services.schema.canonical_schema import CANONICAL_FIELDS, MANDATORY_SOURCE_FIELDS, REQUIRED_CANONICAL_FIELDS
from app.services.schema.validator import validate_normalized_dataframe

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_UPLOADS_DIR = _DATA_DIR / "uploads"
_NORMALIZED_DIR = _DATA_DIR / "normalized"
_ACTIVE_TRANSACTIONS_CSV = _DATA_DIR / "transactions.csv"


def ensure_data_directories() -> None:
    """Ensure data storage directories exist."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    _NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize_native(obj: Any) -> Any:
    """Recursively convert numpy/pandas/bool types to native Python JSON-serializable types."""
    if isinstance(obj, dict):
        return {str(k): _sanitize_native(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [_sanitize_native(v) for v in obj]
    elif isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    elif isinstance(obj, (int, np.integer)):
        return int(obj)
    elif isinstance(obj, (float, np.floating)):
        return float(obj)
    elif pd.isna(obj):
        return None
    return str(obj) if not isinstance(obj, (str, type(None))) else obj


def normalize_dataset(
    raw_csv_path: Union[str, Path],
    mapping_dict: Dict[str, str],
    drop_invalid_amounts: bool = False,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Transform raw CSV to Canonical Schema DataFrame according to mapping_dict.

    Parameters
    ----------
    raw_csv_path : str | Path
        Path to raw external CSV.
    mapping_dict : Dict[str, str]
        Dictionary of {source_column: canonical_field_name}.
    drop_invalid_amounts : bool
        Whether to drop rows with invalid amounts instead of flagging.

    Returns
    -------
    Tuple[pd.DataFrame, Dict[str, Any]]
        (normalized_clean_df, data_quality_report)
    """
    raw_csv_path = Path(raw_csv_path)
    if not raw_csv_path.exists():
        raise FileNotFoundError(f"Raw CSV file not found: {raw_csv_path}")

    raw_df = pd.read_csv(raw_csv_path)

    # Invert mapping dict to target -> source
    target_to_source = {v: k for k, v in mapping_dict.items()}

    # Check mandatory source fields
    missing_req = [f for f in MANDATORY_SOURCE_FIELDS if f not in target_to_source]
    if missing_req:
        raise ValueError(
            f"Mapping is missing mandatory field(s): {', '.join(missing_req)}. "
            f"Please ensure sender_account_id, receiver_account_id, amount, and timestamp are mapped."
        )

    canonical_df = pd.DataFrame(index=raw_df.index)

    # Copy mapped fields
    for canonical_name, source_col in target_to_source.items():
        if source_col in raw_df.columns:
            canonical_df[canonical_name] = raw_df[source_col]

    # Preserve any extra optional fields present in raw_df
    unmapped_sources = [c for c in raw_df.columns if c not in mapping_dict]
    for unmapped_col in unmapped_sources:
        if unmapped_col not in canonical_df.columns:
            canonical_df[unmapped_col] = raw_df[unmapped_col]

    # Validate & parse
    val_res = validate_normalized_dataframe(canonical_df, drop_invalid_amounts=drop_invalid_amounts)
    clean_df = val_res["clean_df"]

    # Generate Data Quality Report
    row_count = len(clean_df)
    unique_senders = clean_df["sender_account_id"].nunique() if "sender_account_id" in clean_df.columns else 0
    unique_receivers = clean_df["receiver_account_id"].nunique() if "receiver_account_id" in clean_df.columns else 0
    unique_txns = clean_df["transaction_id"].nunique() if "transaction_id" in clean_df.columns else 0

    date_range = {}
    if "timestamp" in clean_df.columns and pd.api.types.is_datetime64_any_dtype(clean_df["timestamp"]):
        date_range = {
            "start": str(clean_df["timestamp"].min()),
            "end": str(clean_df["timestamp"].max()),
            "days_span": round((clean_df["timestamp"].max() - clean_df["timestamp"].min()).total_seconds() / 86400, 2),
        }

    missing_vals = clean_df.isnull().sum().to_dict()
    dup_cols = [c for c in ["sender_account_id", "receiver_account_id", "amount", "timestamp"] if c in clean_df.columns]
    dup_count = int(clean_df.duplicated(subset=dup_cols).sum()) if dup_cols else 0

    fraud_dist = {"has_label": False}
    if "is_mule_pattern" in clean_df.columns and clean_df["is_mule_pattern"].notna().any():
        counts = clean_df["is_mule_pattern"].value_counts().to_dict()
        pos = counts.get(1, 0)
        neg = counts.get(0, 0)
        fraud_dist = {
            "has_label": True,
            "legitimate_count": int(neg),
            "fraud_count": int(pos),
            "fraud_rate_pct": round((pos / max(row_count, 1)) * 100, 3),
        }

    quality_report = _sanitize_native({
        "row_count": row_count,
        "unique_senders": unique_senders,
        "unique_receivers": unique_receivers,
        "unique_transactions": unique_txns,
        "date_range": date_range,
        "missing_values": missing_vals,
        "duplicate_count": dup_count,
        "invalid_amount_count": val_res["invalid_amount_count"],
        "timestamp_source": val_res["timestamp_source"],
        "fraud_label_distribution": fraud_dist,
        "mapped_columns_count": len(mapping_dict),
        "unmapped_columns_count": len(unmapped_sources),
        "can_predict": val_res["can_predict"],
        "can_train": val_res["can_train"],
    })

    return clean_df, quality_report


def normalize_and_save_dataset(
    raw_csv_path: Union[str, Path],
    mapping_dict: Dict[str, str],
    upload_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Normalize raw CSV, persist normalized copy, and update active transactions.csv link.
    """
    ensure_data_directories()
    raw_csv_path = Path(raw_csv_path)

    if not upload_id:
        upload_id = f"up_{uuid.uuid4().hex[:8]}"

    clean_df, quality_report = normalize_dataset(raw_csv_path, mapping_dict)

    # Persist normalized canonical CSV
    normalized_path = _NORMALIZED_DIR / f"{upload_id}_normalized.csv"
    clean_df.to_csv(normalized_path, index=False)

    # Update active transactions.csv for existing downstream ML code
    clean_df.to_csv(_ACTIVE_TRANSACTIONS_CSV, index=False)

    logger.info("Successfully normalized & active dataset saved -> %s", _ACTIVE_TRANSACTIONS_CSV)

    return {
        "upload_id": upload_id,
        "raw_csv_path": str(raw_csv_path),
        "normalized_csv_path": str(normalized_path),
        "active_csv_path": str(_ACTIVE_TRANSACTIONS_CSV),
        "row_count": len(clean_df),
        "columns": list(clean_df.columns),
        "quality_report": quality_report,
    }
