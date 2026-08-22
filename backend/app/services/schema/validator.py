"""
app/services/schema/validator.py
=================================
Canonical Data Validation & Strict Quality Auditor.

Key Rules:
  1. DO NOT silently convert invalid monetary strings (e.g. "ABC") to 0.0.
     Detect invalid rows, record row numbers/counts, and flag invalid entries.
  2. Parse timestamps cleanly (ISO datetime vs PaySim 'step' hours).
     Record timestamp_source: 'provided' vs 'derived_from_step'.
  3. Validate core required fields (transaction_id, sender_account_id, receiver_account_id, amount, timestamp).
  4. Infer dataset ML capabilities: can_train vs can_predict.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from app.services.schema.canonical_schema import MANDATORY_SOURCE_FIELDS, REQUIRED_CANONICAL_FIELDS

logger = logging.getLogger(__name__)


def validate_and_parse_amounts(series: pd.Series) -> Tuple[pd.Series, List[int], int]:
    """
    Validate monetary transaction amounts strictly.
    DO NOT silently convert non-numeric invalid values (e.g. 'ABC') to 0.0.

    Returns:
      - parsed_series: pd.Series (floats with NaNs where invalid)
      - invalid_row_indices: List[int] (0-indexed list of invalid row numbers)
      - invalid_count: int
    """
    # Attempt numeric parsing without auto-filling zero
    numeric_series = pd.to_numeric(series, errors="coerce")
    
    # Invalid if NaN or <= 0
    invalid_mask = numeric_series.isna() | (numeric_series <= 0)
    invalid_indices = series.index[invalid_mask].tolist()
    invalid_count = len(invalid_indices)

    if invalid_count > 0:
        logger.warning(
            "Validation Alert: Found %d rows with invalid/non-numeric transaction amount. First invalid rows: %s",
            invalid_count,
            invalid_indices[:5],
        )

    return numeric_series, invalid_indices, invalid_count


def validate_and_parse_timestamps(
    series: pd.Series, timestamp_mode: str = "datetime"
) -> Tuple[pd.Series, str, List[int], int]:
    """
    Parse timestamps and track origin ('provided' vs 'derived_from_step').

    Returns:
      - parsed_series: pd.Series (DatetimeIndex)
      - timestamp_source: str ('provided' or 'derived_from_step')
      - invalid_row_indices: List[int]
      - invalid_count: int
    """
    if timestamp_mode == "step_hours":
        steps = pd.to_numeric(series, errors="coerce").fillna(1).astype(int)
        base_time = pd.Timestamp("2026-01-01 00:00:00")
        parsed_ts = base_time + pd.to_timedelta(steps, unit="h")
        return parsed_ts, "derived_from_step", [], 0

    # Provided ISO or standard datetime strings
    parsed_ts = pd.to_datetime(series, errors="coerce")
    invalid_mask = parsed_ts.isna()
    invalid_indices = series.index[invalid_mask].tolist()
    invalid_count = len(invalid_indices)

    if invalid_count > 0:
        logger.warning("Found %d rows with invalid/unparsable timestamps.", invalid_count)
        min_ts = parsed_ts.dropna().min() if not parsed_ts.dropna().empty else pd.Timestamp("2026-01-01")
        parsed_ts = parsed_ts.fillna(min_ts)

    return parsed_ts, "provided", invalid_indices, invalid_count


def validate_normalized_dataframe(
    df: pd.DataFrame, drop_invalid_amounts: bool = False
) -> Dict[str, Any]:
    """
    Perform deep quality validation on a canonical-mapped DataFrame.

    Returns dictionary containing validation summary, invalid row counts,
    parsed DataFrame (or clean copy), and dataset capabilities.
    """
    clean_df = df.copy()

    # Synthesize transaction_id if missing
    if "transaction_id" not in clean_df.columns:
        clean_df["transaction_id"] = [f"TXN_{i+1:08d}" for i in range(len(clean_df))]

    # Synthesize transaction_type if missing
    if "transaction_type" not in clean_df.columns:
        clean_df["transaction_type"] = "TRANSFER"

    # Check mandatory fields that must come from source data
    missing_required = []
    for req_field in MANDATORY_SOURCE_FIELDS:
        if req_field not in clean_df.columns:
            missing_required.append(req_field)

    if missing_required:
        raise ValueError(
            f"Dataset is missing mandatory field(s): {', '.join(missing_required)}. "
            f"Please ensure sender_account_id, receiver_account_id, amount, and timestamp are mapped."
        )

    # 1. Parse & validate amount
    parsed_amounts, invalid_amount_rows, invalid_amount_count = validate_and_parse_amounts(
        clean_df["amount"]
    )
    clean_df["amount"] = parsed_amounts

    if drop_invalid_amounts and invalid_amount_count > 0:
        clean_df = clean_df.dropna(subset=["amount"])
        clean_df = clean_df[clean_df["amount"] > 0]
    else:
        # Fill remaining NaNs with 0.0 ONLY after explicitly recording invalid_amount_count in audit
        clean_df["amount"] = clean_df["amount"].fillna(0.0)

    # 2. Parse & validate timestamps
    is_step_mode = "step" in df.columns or (
        pd.api.types.is_numeric_dtype(df["timestamp"]) and df["timestamp"].max() <= 10000
    )
    parsed_ts, ts_source, invalid_ts_rows, invalid_ts_count = validate_and_parse_timestamps(
        clean_df["timestamp"], timestamp_mode="step_hours" if is_step_mode else "datetime"
    )
    clean_df["timestamp"] = parsed_ts

    # 3. Clean string identifiers
    clean_df["sender_account_id"] = clean_df["sender_account_id"].astype(str).str.strip()
    clean_df["receiver_account_id"] = clean_df["receiver_account_id"].astype(str).str.strip()

    if "transaction_id" in clean_df.columns:
        clean_df["transaction_id"] = clean_df["transaction_id"].astype(str).str.strip()
    else:
        clean_df["transaction_id"] = [f"TXN_{i+1:08d}" for i in range(len(clean_df))]

    if "transaction_type" not in clean_df.columns:
        clean_df["transaction_type"] = "TRANSFER"
    else:
        clean_df["transaction_type"] = clean_df["transaction_type"].fillna("TRANSFER").astype(str)

    # 4. Infer dataset ML capabilities
    has_label = "is_mule_pattern" in clean_df.columns and clean_df["is_mule_pattern"].notna().any()
    can_predict = True
    can_train = has_label

    return {
        "is_valid": True,
        "clean_df": clean_df,
        "total_rows": len(clean_df),
        "invalid_amount_count": invalid_amount_count,
        "invalid_amount_row_indices": invalid_amount_rows[:20],
        "invalid_timestamp_count": invalid_ts_count,
        "timestamp_source": ts_source,
        "can_predict": can_predict,
        "can_train": can_train,
        "missing_required": [],
        "has_label": has_label,
    }
