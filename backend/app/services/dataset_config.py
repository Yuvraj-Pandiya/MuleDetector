"""
app/services/dataset_config.py
================================
Configurable dataset mapping layer for MuleDetector.

Canonical internal schema fields:
  - transaction_id    : str (unique transaction identifier)
  - timestamp         : datetime64[ns]
  - sender_id         : str (sender account identifier -> sender_account_id)
  - receiver_id       : str (receiver account identifier -> receiver_account_id)
  - amount            : float64 (monetary transaction amount)
  - transaction_type  : str (categorical transaction type e.g. TRANSFER, CASH_OUT)
  - fraud_label       : int (0=legitimate, 1=mule/fraud -> is_mule_pattern)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class DatasetSchemaMapping:
    """Mapping configuration for translating external raw CSV headers to internal canonical fields."""
    name: str
    sender_id_col: str
    receiver_id_col: str
    amount_col: str
    timestamp_col: str
    transaction_type_col: Optional[str] = None
    transaction_id_col: Optional[str] = None
    fraud_label_col: Optional[str] = None
    
    # Custom timestamp transformation mode: 'datetime' or 'step_hours'
    timestamp_mode: str = "datetime"
    
    # Internal canonical column targets
    TARGET_SENDER_ID: str = "sender_account_id"
    TARGET_RECEIVER_ID: str = "receiver_account_id"
    TARGET_TIMESTAMP: str = "timestamp"
    TARGET_AMOUNT: str = "amount"
    TARGET_TRANSACTION_TYPE: str = "transaction_type"
    TARGET_TRANSACTION_ID: str = "transaction_id"
    TARGET_FRAUD_LABEL: str = "is_mule_pattern"


# Preset 1: Internal Canonical Schema (Standard Synthetic / Processed Format)
CANONICAL_SCHEMA_MAPPING = DatasetSchemaMapping(
    name="canonical",
    sender_id_col="sender_account_id",
    receiver_id_col="receiver_account_id",
    amount_col="amount",
    timestamp_col="timestamp",
    transaction_type_col="transaction_type",
    transaction_id_col="transaction_id",
    fraud_label_col="is_mule_pattern",
    timestamp_mode="datetime",
)

# Preset 2: PaySim Financial Transaction Dataset Schema
PAYSIM_SCHEMA_MAPPING = DatasetSchemaMapping(
    name="paysim",
    sender_id_col="nameOrig",
    receiver_id_col="nameDest",
    amount_col="amount",
    timestamp_col="step",
    transaction_type_col="type",
    transaction_id_col=None,          # Unavailable in PaySim — synthesized at load time
    fraud_label_col="isFraud",        # PaySim ground truth column
    timestamp_mode="step_hours",      # 1 step = 1 hour from simulation start
)

# Preset 3: Standard Alternate Field Names Preset
ALT_STANDARD_SCHEMA_MAPPING = DatasetSchemaMapping(
    name="alt_standard",
    sender_id_col="sender_id",
    receiver_id_col="receiver_id",
    amount_col="amount",
    timestamp_col="timestamp",
    transaction_type_col="transaction_type",
    transaction_id_col="transaction_id",
    fraud_label_col="fraud_label",
    timestamp_mode="datetime",
)

KNOWN_SCHEMAS: Dict[str, DatasetSchemaMapping] = {
    "canonical": CANONICAL_SCHEMA_MAPPING,
    "paysim": PAYSIM_SCHEMA_MAPPING,
    "alt_standard": ALT_STANDARD_SCHEMA_MAPPING,
}


def detect_schema_mapping(columns: list[str]) -> DatasetSchemaMapping:
    """
    Auto-detect which known schema mapping matches the CSV columns.
    
    Parameters
    ----------
    columns : list[str]
        Header columns of the CSV DataFrame.

    Returns
    -------
    DatasetSchemaMapping
        The matched DatasetSchemaMapping config.
    """
    col_set = set(columns)

    # Check PaySim
    if {"nameOrig", "nameDest", "amount", "step"}.issubset(col_set):
        return PAYSIM_SCHEMA_MAPPING

    # Check Canonical
    if {"sender_account_id", "receiver_account_id", "amount", "timestamp"}.issubset(col_set):
        return CANONICAL_SCHEMA_MAPPING

    # Check Alt Standard
    if {"sender_id", "receiver_id", "amount", "timestamp"}.issubset(col_set):
        return ALT_STANDARD_SCHEMA_MAPPING

    # Default fallback to canonical
    return CANONICAL_SCHEMA_MAPPING
