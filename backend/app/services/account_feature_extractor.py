"""
app/services/account_feature_extractor.py
===========================================
Account-Level Feature Extractor for MuleDetector.

Aggregates transaction-level data into account-level entities, computing
lifetime, transaction counts, inbound/outbound volume splits, and risk labels.

Strictly preserves temporal causality: supports point-in-time cutoff filtering
to prevent future data leakage.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
import pandas as pd

from app.services.preprocessing_pipeline import preprocess_transactions

logger = logging.getLogger(__name__)


def extract_account_features(
    data_input: Union[str, Path, pd.DataFrame],
    cutoff_timestamp: Optional[Union[str, pd.Timestamp]] = None,
    max_rows: Optional[int] = None,
) -> pd.DataFrame:
    """
    Extract account-level aggregated features from transaction-level data.

    Parameters
    ----------
    data_input : str | Path | pd.DataFrame
        Path to transaction CSV or cleaned transaction DataFrame.
    cutoff_timestamp : Optional[str | pd.Timestamp]
        If specified, filter out all transactions occurring after this cutoff.
        Guarantees point-in-time calculation (zero future data leakage).
    max_rows : Optional[int]
        Optional row limit for fast sampling.

    Returns
    -------
    pd.DataFrame
        Account-level DataFrame where each row represents one account with columns:
          - account_id
          - first_transaction_time
          - last_transaction_time
          - account_lifetime
          - total_transaction_count
          - total_incoming_count
          - total_outgoing_count
          - total_incoming_amount
          - total_outgoing_amount
          - is_mule_pattern (optional ground truth label if present)
    """
    t0 = time.perf_counter()

    # 1. Ingest & Preprocess Transaction Data
    if isinstance(data_input, (str, Path)):
        df, _, _ = preprocess_transactions(data_input, max_rows=max_rows)
    elif isinstance(data_input, pd.DataFrame):
        df = data_input.copy()
    else:
        raise TypeError(f"Unsupported data_input type: {type(data_input)}")

    if df.empty:
        logger.warning("[AccountFeatureExtractor] Input DataFrame is empty.")
        return pd.DataFrame()

    # 2. Point-in-Time Cutoff Filter (Causality Enforcement)
    if cutoff_timestamp is not None:
        cutoff_dt = pd.to_datetime(cutoff_timestamp)
        df = df[df["timestamp"] <= cutoff_dt].copy()
        logger.info("[AccountFeatureExtractor] Filtered transactions <= %s (%d rows remaining)", cutoff_dt, len(df))

    has_label = "is_mule_pattern" in df.columns

    # 3. Outbound Aggregation (Grouped by sender_account_id)
    outbound = (
        df.groupby("sender_account_id")
        .agg(
            first_out=("timestamp", "min"),
            last_out=("timestamp", "max"),
            total_outgoing_count=("amount", "count"),
            total_outgoing_amount=("amount", "sum"),
            mule_out=("is_mule_pattern", "max") if has_label else ("amount", lambda x: 0),
        )
        .reset_index()
        .rename(columns={"sender_account_id": "account_id"})
    )

    # 4. Inbound Aggregation (Grouped by receiver_account_id)
    inbound = (
        df.groupby("receiver_account_id")
        .agg(
            first_in=("timestamp", "min"),
            last_in=("timestamp", "max"),
            total_incoming_count=("amount", "count"),
            total_incoming_amount=("amount", "sum"),
            mule_in=("is_mule_pattern", "max") if has_label else ("amount", lambda x: 0),
        )
        .reset_index()
        .rename(columns={"receiver_account_id": "account_id"})
    )

    # 5. Outer Join Outbound & Inbound on account_id
    merged = pd.merge(outbound, inbound, on="account_id", how="outer")

    # 6. Compute Unified Account Features
    # Timestamps
    first_ts = merged[["first_out", "first_in"]].min(axis=1)
    last_ts = merged[["last_out", "last_in"]].max(axis=1)

    # Account lifetime in fractional days
    lifetime_days = (last_ts - first_ts).dt.total_seconds() / 86400.0

    # Counts & Amounts
    inc_count = merged["total_incoming_count"].fillna(0).astype(int)
    out_count = merged["total_outgoing_count"].fillna(0).astype(int)
    tot_count = inc_count + out_count

    inc_amt = merged["total_incoming_amount"].fillna(0.0).round(2)
    out_amt = merged["total_outgoing_amount"].fillna(0.0).round(2)

    account_df = pd.DataFrame(
        {
            "account_id": merged["account_id"],
            "first_transaction_time": first_ts,
            "last_transaction_time": last_ts,
            "account_lifetime": lifetime_days.round(4),
            "total_transaction_count": tot_count,
            "total_incoming_count": inc_count,
            "total_outgoing_count": out_count,
            "total_incoming_amount": inc_amt,
            "total_outgoing_amount": out_amt,
        }
    )

    if has_label:
        mule_label = np.maximum(
            merged["mule_out"].fillna(0).astype(int),
            merged["mule_in"].fillna(0).astype(int),
        )
        account_df["is_mule_pattern"] = mule_label

    # Sort accounts by account_id for consistent ordering
    account_df = account_df.sort_values("account_id").reset_index(drop=True)

    elapsed = round(time.perf_counter() - t0, 3)
    logger.info(
        "[AccountFeatureExtractor] Extracted %d unique account rows from %d transactions in %.3fs",
        len(account_df),
        len(df),
        elapsed,
    )

    return account_df
