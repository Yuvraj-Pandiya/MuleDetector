"""
app/services/features_anomaly.py
----------------------------------
Statistical anomaly features per account.

Output columns (exactly as per docs/feature_schema.md):
  amount_zscore_avg, round_number_txn_ratio, odd_hour_txn_ratio

Definitions
-----------
amount_zscore_avg
    Z-score of this account's average transaction amount relative to the
    population of all account averages.
    z = (avg_i - mu_pop) / (std_pop + eps)

round_number_txn_ratio
    Fraction of this account's transactions where amount % 100 == 0
    (i.e. divisible by 100 with no remainder).

odd_hour_txn_ratio
    Fraction of transactions sent or received between 00:00 and 05:59
    (local time — the dataset has no timezone info so we treat as-is).
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

_EPS = 1e-9

ANOMALY_COLUMNS: list[str] = [
    "amount_zscore_avg",
    "round_number_txn_ratio",
    "odd_hour_txn_ratio",
]


def compute_anomaly_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute anomaly/statistical features per account.

    Parameters
    ----------
    df : pd.DataFrame
        Transaction DataFrame with at least:
        sender_account_id, receiver_account_id, amount, timestamp.

    Returns
    -------
    pd.DataFrame
        Columns: ``account_id`` + ANOMALY_COLUMNS.
        All float, non-null.
    """
    t0 = time.perf_counter()

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    # ------------------------------------------------------------------
    # Build unified "participation" view: one row per (account, txn)
    # from both sender and receiver perspectives
    # ------------------------------------------------------------------
    sent = df[["sender_account_id", "amount", "timestamp"]].rename(
        columns={"sender_account_id": "account_id"}
    )
    recv = df[["receiver_account_id", "amount", "timestamp"]].rename(
        columns={"receiver_account_id": "account_id"}
    )
    txns = pd.concat([sent, recv], ignore_index=True)

    # ------------------------------------------------------------------
    # 1. amount_zscore_avg
    #    Per-account mean, then z-score relative to all accounts' means
    # ------------------------------------------------------------------
    per_account_avg = txns.groupby("account_id")["amount"].mean()

    pop_mean = per_account_avg.mean()
    pop_std  = per_account_avg.std(ddof=0)  # population std

    amount_zscore_avg = ((per_account_avg - pop_mean) / (pop_std + _EPS)).rename(
        "amount_zscore_avg"
    )

    # ------------------------------------------------------------------
    # 2. round_number_txn_ratio
    #    Fraction of txns where amount % 100 == 0
    # ------------------------------------------------------------------
    txns["is_round"] = (txns["amount"] % 100 == 0).astype(int)
    round_ratio = (
        txns.groupby("account_id")["is_round"].mean().rename("round_number_txn_ratio")
    )

    # ------------------------------------------------------------------
    # 3. odd_hour_txn_ratio
    #    Fraction of txns between 00:00 and 05:59 (hour < 6)
    # ------------------------------------------------------------------
    txns["hour"] = txns["timestamp"].dt.hour
    txns["is_odd_hour"] = (txns["hour"] < 6).astype(int)
    odd_ratio = (
        txns.groupby("account_id")["is_odd_hour"].mean().rename("odd_hour_txn_ratio")
    )

    # ------------------------------------------------------------------
    # Assemble
    # ------------------------------------------------------------------
    result = (
        pd.DataFrame(index=per_account_avg.index)
        .join(amount_zscore_avg)
        .join(round_ratio)
        .join(odd_ratio)
        .fillna(0.0)
        .reset_index()
    )
    result.rename(columns={"index": "account_id"}, inplace=True)

    # Type enforcement: all anomaly cols are float
    result[ANOMALY_COLUMNS] = result[ANOMALY_COLUMNS].astype(float)

    elapsed = time.perf_counter() - t0
    print(f"[anomaly] Total time: {elapsed:.3f}s")

    return result[["account_id"] + ANOMALY_COLUMNS]
