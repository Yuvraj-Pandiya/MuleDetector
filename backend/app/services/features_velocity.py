"""
app/services/features_velocity.py
----------------------------------
Extended velocity feature computation per account_id.

Output columns:
  - Time-window transaction counts:
      txn_count_5min, txn_count_15min, txn_count_1h, txn_count_6h, txn_count_24h, txn_count_7d
  - Time-window directional amounts:
      amount_in_1h, amount_out_1h, amount_in_24h, amount_out_24h, amount_in_7d, amount_out_7d
      (aliases for schema contract: total_amount_in_24h, total_amount_out_24h)
  - Amount distribution metrics:
      max_transaction_amount, average_transaction_amount, median_transaction_amount
      (alias: avg_transaction_amount)
  - Velocity change indicators:
      transaction_velocity_change, recent_volume_vs_historical_volume
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Epsilon prevents divide-by-zero in downstream ratio features
_EPS = 1e-9

# High-volume threshold used for is_new_high_volume_flag (shared with behavioral)
HIGH_VOLUME_TXN_THRESHOLD = 10

# Extended velocity columns
EXTENDED_VELOCITY_COLUMNS: list[str] = [
    # Counts
    "txn_count_5min",
    "txn_count_15min",
    "txn_count_1h",
    "txn_count_6h",
    "txn_count_24h",
    "txn_count_7d",
    # Amounts
    "amount_in_1h",
    "amount_out_1h",
    "amount_in_24h",
    "amount_out_24h",
    "amount_in_7d",
    "amount_out_7d",
    # Backward compatibility aliases
    "total_amount_out_24h",
    "total_amount_in_24h",
    # Amount stats
    "max_transaction_amount",
    "average_transaction_amount",
    "avg_transaction_amount",
    "median_transaction_amount",
    # Velocity change indicators
    "transaction_velocity_change",
    "recent_volume_vs_historical_volume",
]

# Standard contract list for feature_pipeline.py
VELOCITY_COLUMNS: list[str] = [
    "txn_count_1h",
    "txn_count_24h",
    "txn_count_7d",
    "total_amount_out_24h",
    "total_amount_in_24h",
    "avg_transaction_amount",
    "max_transaction_amount",
    "txn_count_5min",
    "txn_count_15min",
    "txn_count_6h",
    "amount_in_1h",
    "amount_out_1h",
    "amount_in_7d",
    "amount_out_7d",
    "median_transaction_amount",
    "transaction_velocity_change",
    "recent_volume_vs_historical_volume",
]


def compute_velocity_features(
    df: pd.DataFrame,
    as_of_timestamp: pd.Timestamp | str | None = None,
) -> pd.DataFrame:
    """
    Compute extended velocity features for every account that appears as a sender
    or receiver.

    Parameters
    ----------
    df : pd.DataFrame
        Transaction DataFrame (must contain: timestamp, sender_account_id,
        receiver_account_id, amount).
    as_of_timestamp : pd.Timestamp | str | None
        Cutoff timestamp simulating prediction time (t_ref). If None, uses max(timestamp).
        Guarantees zero future transaction data leakage.

    Returns
    -------
    pd.DataFrame
        DataFrame with column ``account_id`` + all velocity feature columns.
    """
    if df.empty:
        return pd.DataFrame(columns=["account_id"] + EXTENDED_VELOCITY_COLUMNS)

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # 1. Reference Timestamp (Point-in-Time Causality Enforcement)
    if as_of_timestamp is not None:
        t_ref = pd.to_datetime(as_of_timestamp)
        df = df[df["timestamp"] <= t_ref].copy()
    else:
        t_ref = df["timestamp"].max()

    if df.empty:
        return pd.DataFrame(columns=["account_id"] + EXTENDED_VELOCITY_COLUMNS)

    # 2. Build Unified View: (account_id, timestamp, amount, direction)
    sent = df[["timestamp", "sender_account_id", "amount"]].rename(
        columns={"sender_account_id": "account_id"}
    )
    sent["direction"] = "out"

    received = df[["timestamp", "receiver_account_id", "amount"]].rename(
        columns={"receiver_account_id": "account_id"}
    )
    received["direction"] = "in"

    txns = pd.concat([sent, received], ignore_index=True)
    txns["amount"] = pd.to_numeric(txns["amount"], errors="coerce").fillna(0.0)

    # 3. Vectorised Time-Window Flags (relative to t_ref)
    delta = t_ref - txns["timestamp"]
    txns["in_5m"]  = (delta >= pd.Timedelta(0)) & (delta <= pd.Timedelta(minutes=5))
    txns["in_15m"] = (delta >= pd.Timedelta(0)) & (delta <= pd.Timedelta(minutes=15))
    txns["in_1h"]  = (delta >= pd.Timedelta(0)) & (delta <= pd.Timedelta(hours=1))
    txns["in_6h"]  = (delta >= pd.Timedelta(0)) & (delta <= pd.Timedelta(hours=6))
    txns["in_24h"] = (delta >= pd.Timedelta(0)) & (delta <= pd.Timedelta(hours=24))
    txns["in_7d"]  = (delta >= pd.Timedelta(0)) & (delta <= pd.Timedelta(days=7))

    # Vectorised Directional Amount Columns
    txns["amt_in_1h"]   = np.where(txns["in_1h"]  & (txns["direction"] == "in"),  txns["amount"], 0.0)
    txns["amt_out_1h"]  = np.where(txns["in_1h"]  & (txns["direction"] == "out"), txns["amount"], 0.0)

    txns["amt_in_24h"]  = np.where(txns["in_24h"] & (txns["direction"] == "in"),  txns["amount"], 0.0)
    txns["amt_out_24h"] = np.where(txns["in_24h"] & (txns["direction"] == "out"), txns["amount"], 0.0)

    txns["amt_in_7d"]   = np.where(txns["in_7d"]  & (txns["direction"] == "in"),  txns["amount"], 0.0)
    txns["amt_out_7d"]  = np.where(txns["in_7d"]  & (txns["direction"] == "out"), txns["amount"], 0.0)

    # 4. Fast Vectorised Aggregations by account_id
    grp = txns.groupby("account_id")

    agg_df = grp.agg(
        txn_count_5min=("in_5m", "sum"),
        txn_count_15min=("in_15m", "sum"),
        txn_count_1h=("in_1h", "sum"),
        txn_count_6h=("in_6h", "sum"),
        txn_count_24h=("in_24h", "sum"),
        txn_count_7d=("in_7d", "sum"),
        amount_in_1h=("amt_in_1h", "sum"),
        amount_out_1h=("amt_out_1h", "sum"),
        amount_in_24h=("amt_in_24h", "sum"),
        amount_out_24h=("amt_out_24h", "sum"),
        amount_in_7d=("amt_in_7d", "sum"),
        amount_out_7d=("amt_out_7d", "sum"),
        max_transaction_amount=("amount", "max"),
        average_transaction_amount=("amount", "mean"),
        median_transaction_amount=("amount", "median"),
    ).reset_index()

    # 5. Derived Velocity Change Indicators
    # A. Velocity change: 1h txn count vs 24h average hourly txn count
    # baseline_hourly_txn_count = (txn_count_24h / 24.0)
    # velocity_change = txn_count_1h / (baseline_hourly_txn_count + eps)
    baseline_hourly_txns = (agg_df["txn_count_24h"] / 24.0) + _EPS
    agg_df["transaction_velocity_change"] = (agg_df["txn_count_1h"] / baseline_hourly_txns).round(4)

    # B. Volume change: 1h total volume (in+out) vs 24h average hourly volume
    recent_1h_vol = agg_df["amount_in_1h"] + agg_df["amount_out_1h"]
    baseline_hourly_vol = ((agg_df["amount_in_24h"] + agg_df["amount_out_24h"]) / 24.0) + _EPS
    agg_df["recent_volume_vs_historical_volume"] = (recent_1h_vol / baseline_hourly_vol).round(4)

    # 6. Backward Compatibility Aliases
    agg_df["total_amount_out_24h"] = agg_df["amount_out_24h"]
    agg_df["total_amount_in_24h"]  = agg_df["amount_in_24h"]
    agg_df["avg_transaction_amount"] = agg_df["average_transaction_amount"]

    # Fill NaNs & Rounding
    int_cols = [
        "txn_count_5min", "txn_count_15min", "txn_count_1h",
        "txn_count_6h", "txn_count_24h", "txn_count_7d"
    ]
    float_cols = [c for c in EXTENDED_VELOCITY_COLUMNS if c not in int_cols]

    agg_df[int_cols] = agg_df[int_cols].fillna(0).astype(int)
    agg_df[float_cols] = agg_df[float_cols].fillna(0.0).round(4).astype(float)

    # Return in clean order
    out_cols = ["account_id"] + [c for c in EXTENDED_VELOCITY_COLUMNS if c in agg_df.columns]
    return agg_df[out_cols]
