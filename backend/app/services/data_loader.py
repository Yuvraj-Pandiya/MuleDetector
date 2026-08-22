"""
app/services/data_loader.py
---------------------------
Centralised, configurable CSV ingestion, validation, and quality reporting
for MuleDetector.

Supports canonical schemas, PaySim dataset, and custom schema mappings.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

import pandas as pd

from app.services.dataset_config import (
    CANONICAL_SCHEMA_MAPPING,
    DatasetSchemaMapping,
    detect_schema_mapping,
)

logger = logging.getLogger(__name__)


def generate_data_quality_report(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate a comprehensive Data Quality Report from a cleaned transaction DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned transaction DataFrame in canonical schema.

    Returns
    -------
    Dict[str, Any]
        Dictionary containing quality metrics.
    """
    row_count = len(df)
    unique_senders = df["sender_account_id"].nunique() if "sender_account_id" in df.columns else 0
    unique_receivers = df["receiver_account_id"].nunique() if "receiver_account_id" in df.columns else 0
    unique_transactions = df["transaction_id"].nunique() if "transaction_id" in df.columns else 0

    # Date range
    date_range = {}
    if "timestamp" in df.columns and pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        date_range = {
            "start": str(df["timestamp"].min()),
            "end": str(df["timestamp"].max()),
            "days_span": round((df["timestamp"].max() - df["timestamp"].min()).total_seconds() / 86400, 2),
        }

    # Missing values per column
    missing_values = df.isnull().sum().to_dict()

    # Duplicate transactions count (on sender, receiver, amount, timestamp)
    dup_cols = [c for c in ["sender_account_id", "receiver_account_id", "amount", "timestamp"] if c in df.columns]
    duplicate_count = int(df.duplicated(subset=dup_cols).sum()) if dup_cols else 0

    # Invalid amount detection
    invalid_amount_count = 0
    if "amount" in df.columns:
        invalid_amount_count = int(((df["amount"].isna()) | (df["amount"] <= 0)).sum())

    # Fraud / Label distribution
    fraud_distribution = {"has_label": False}
    if "is_mule_pattern" in df.columns:
        counts = df["is_mule_pattern"].value_counts().to_dict()
        total = len(df)
        pos = counts.get(1, 0)
        neg = counts.get(0, 0)
        fraud_distribution = {
            "has_label": True,
            "legitimate_count": neg,
            "fraud_count": pos,
            "fraud_rate_pct": round((pos / max(total, 1)) * 100, 3),
        }

    return {
        "row_count": row_count,
        "unique_senders": unique_senders,
        "unique_receivers": unique_receivers,
        "unique_transactions": unique_transactions,
        "date_range": date_range,
        "missing_values": missing_values,
        "duplicate_count": duplicate_count,
        "invalid_amount_count": invalid_amount_count,
        "fraud_label_distribution": fraud_distribution,
    }


def load_transactions(
    csv_path: Union[str, Path],
    schema_mapping: Optional[DatasetSchemaMapping] = None,
    max_rows: Optional[int] = None,
) -> pd.DataFrame:
    """
    Read a transaction CSV, map fields to canonical schema, validate datatypes,
    and parse timestamps.

    Parameters
    ----------
    csv_path : str | Path
        Path to the transaction CSV file.
    schema_mapping : Optional[DatasetSchemaMapping]
        Custom mapping configuration. If None, auto-detected from CSV headers.
    max_rows : Optional[int]
        Limit number of rows read (useful for fast sampling of large datasets like PaySim).

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame with canonical columns:
        ``sender_account_id``, ``receiver_account_id``, ``amount``, ``timestamp``,
        ``transaction_id``, ``transaction_type``, and optionally ``is_mule_pattern``.

    Raises
    ------
    FileNotFoundError
        If csv_path does not exist.
    ValueError
        If required core columns are missing or validation fails.
    """
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"Transaction file not found: {csv_path}")

    # Read header first to detect schema
    header_df = pd.read_csv(csv_path, nrows=2)
    
    if schema_mapping is None:
        schema_mapping = detect_schema_mapping(header_df.columns.tolist())

    logger.info("Ingesting '%s' using schema mapping '%s'", csv_path.name, schema_mapping.name)

    # Validate essential source columns exist in CSV
    missing_required = []
    for field_name, source_col in [
        ("sender_id", schema_mapping.sender_id_col),
        ("receiver_id", schema_mapping.receiver_id_col),
        ("amount", schema_mapping.amount_col),
        ("timestamp", schema_mapping.timestamp_col),
    ]:
        if source_col not in header_df.columns:
            missing_required.append(f"{field_name} ('{source_col}')")

    if missing_required:
        raise ValueError(
            f"CSV file '{csv_path.name}' is missing required column(s) for schema '{schema_mapping.name}': "
            + ", ".join(missing_required)
            + f". Found columns: {list(header_df.columns)}"
        )

    # Read full CSV (or sample if max_rows specified)
    df = pd.read_csv(csv_path, nrows=max_rows)

    # Prepare canonical columns DataFrame
    res = pd.DataFrame(index=df.index)

    # 1. Sender & Receiver Account IDs
    res["sender_account_id"] = df[schema_mapping.sender_id_col].astype(str)
    res["receiver_account_id"] = df[schema_mapping.receiver_id_col].astype(str)

    # 2. Amount parsing & validation
    res["amount"] = pd.to_numeric(df[schema_mapping.amount_col], errors="coerce")
    invalid_amounts = (res["amount"].isna()) | (res["amount"] <= 0)
    if invalid_amounts.any():
        logger.warning(
            "Found %d rows with invalid/non-numeric amount in '%s'. Coercing NaNs to 0.0.",
            invalid_amounts.sum(),
            csv_path.name,
        )
        res["amount"] = res["amount"].fillna(0.0)

    # 3. Timestamp parsing
    if schema_mapping.timestamp_mode == "step_hours":
        # Convert integer step (hours since start) to datetime starting at 2026-01-01
        steps = pd.to_numeric(df[schema_mapping.timestamp_col], errors="coerce").fillna(1).astype(int)
        base_time = pd.Timestamp("2026-01-01 00:00:00")
        res["timestamp"] = base_time + pd.to_timedelta(steps, unit="h")
    else:
        res["timestamp"] = pd.to_datetime(df[schema_mapping.timestamp_col], errors="coerce")
        if res["timestamp"].isna().any():
            logger.warning("Found NaNs during timestamp parsing. Filling NaNs with minimum valid timestamp.")
            min_ts = res["timestamp"].dropna().min() if not res["timestamp"].dropna().empty else pd.Timestamp("2026-01-01")
            res["timestamp"] = res["timestamp"].fillna(min_ts)

    # 4. Transaction ID
    if schema_mapping.transaction_id_col and schema_mapping.transaction_id_col in df.columns:
        res["transaction_id"] = df[schema_mapping.transaction_id_col].astype(str)
    else:
        # Deterministically synthesize transaction_id from row index if unavailable
        res["transaction_id"] = [f"TXN_{i+1:08d}" for i in range(len(df))]

    # 5. Transaction Type (Optional)
    if schema_mapping.transaction_type_col and schema_mapping.transaction_type_col in df.columns:
        res["transaction_type"] = df[schema_mapping.transaction_type_col].astype(str)
    else:
        res["transaction_type"] = "TRANSFER"

    # 6. Fraud Label (Optional ground truth)
    if schema_mapping.fraud_label_col and schema_mapping.fraud_label_col in df.columns:
        res["is_mule_pattern"] = (
            pd.to_numeric(df[schema_mapping.fraud_label_col], errors="coerce")
            .fillna(0)
            .astype(int)
        )

    # Log data quality summary
    report = generate_data_quality_report(res)
    logger.info(
        "Ingested %d rows from '%s' | Senders: %d | Receivers: %d | Duplicates: %d | Fraud rate: %s",
        report["row_count"],
        csv_path.name,
        report["unique_senders"],
        report["unique_receivers"],
        report["duplicate_count"],
        f"{report['fraud_label_distribution'].get('fraud_rate_pct', 'N/A')}%" if report['fraud_label_distribution']['has_label'] else "No label",
    )

    return res


def load_and_clean_dataset(
    csv_path: Union[str, Path],
    schema_mapping: Optional[DatasetSchemaMapping] = None,
    max_rows: Optional[int] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Backward compatible wrapper that reads and cleans dataset,
    returning a tuple of (DataFrame, quality_report_dict).
    """
    df = load_transactions(csv_path=csv_path, schema_mapping=schema_mapping, max_rows=max_rows)
    report = generate_data_quality_report(df)
    return df, report
