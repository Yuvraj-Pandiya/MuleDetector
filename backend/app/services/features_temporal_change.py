"""
app/services/features_temporal_change.py
=========================================
Temporal Behavior-Change Feature Engine for MuleDetector.

Purpose:
Detect when an account's current behavior is significantly different from its
historical baseline (sudden velocity bursts, monetary volume spikes, off-baseline activity).

Guarantees point-in-time causality (uses only transactions <= as_of_timestamp).

Features:
  - current_1h_vs_historical_ratio
  - current_24h_vs_historical_ratio
  - current_amount_vs_historical_ratio
  - transaction_frequency_change
  - average_amount_change
  - activity_spike_score
  - velocity_change_score
"""

from __future__ import annotations

import logging
import pathlib
from typing import Any, Dict, Optional, Tuple, Union

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_EPS = 1e-9

TEMPORAL_CHANGE_COLUMNS: list[str] = [
    "current_1h_vs_historical_ratio",
    "current_24h_vs_historical_ratio",
    "current_amount_vs_historical_ratio",
    "transaction_frequency_change",
    "average_amount_change",
    "activity_spike_score",
    "velocity_change_score",
]


def compute_temporal_change_features(
    df: pd.DataFrame,
    as_of_timestamp: pd.Timestamp | str | None = None,
) -> pd.DataFrame:
    """
    Compute temporal behavior-change features for every account.

    Parameters
    ----------
    df : pd.DataFrame
        Transaction DataFrame (must contain: timestamp, sender_account_id,
        receiver_account_id, amount).
    as_of_timestamp : pd.Timestamp | str | None
        Optional point-in-time reference cutoff. Excludes future transactions.

    Returns
    -------
    pd.DataFrame
        DataFrame with column ``account_id`` + TEMPORAL_CHANGE_COLUMNS.
    """
    if df.empty:
        return pd.DataFrame(columns=["account_id"] + TEMPORAL_CHANGE_COLUMNS)

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    # 1. Point-in-Time Causality Cutoff
    if as_of_timestamp is not None:
        t_ref = pd.to_datetime(as_of_timestamp)
        df = df[df["timestamp"] <= t_ref].copy()
    else:
        t_ref = df["timestamp"].max()

    if df.empty:
        return pd.DataFrame(columns=["account_id"] + TEMPORAL_CHANGE_COLUMNS)

    # 2. Build Unified Account Transactions View
    sent = df[["timestamp", "sender_account_id", "amount"]].rename(
        columns={"sender_account_id": "account_id"}
    )
    received = df[["timestamp", "receiver_account_id", "amount"]].rename(
        columns={"receiver_account_id": "account_id"}
    )

    txns = pd.concat([sent, received], ignore_index=True)
    delta = t_ref - txns["timestamp"]

    txns["in_1h"]  = (delta >= pd.Timedelta(0)) & (delta <= pd.Timedelta(hours=1))
    txns["in_24h"] = (delta >= pd.Timedelta(0)) & (delta <= pd.Timedelta(hours=24))
    txns["date"] = txns["timestamp"].dt.date
    txns["hour"] = txns["timestamp"].dt.hour

    all_accounts = sorted(list(txns["account_id"].unique()))
    grp = txns.groupby("account_id")

    # 3. Separate Historical Baseline (transactions BEFORE current 1h window) vs Recent Window
    t_1h_start = t_ref - pd.Timedelta(hours=1)
    hist_txns = txns[txns["timestamp"] < t_1h_start]

    # If historical transactions exist for account, compute baseline; else fallback to overall
    if not hist_txns.empty:
        hist_grp = hist_txns.groupby("account_id")
        hist_tot_txns = hist_grp.size()
        hist_tot_amt = hist_grp["amount"].sum()
        hist_act_days = hist_grp["date"].nunique().clip(lower=1)
        hist_act_hours = hist_grp["hour"].nunique().clip(lower=1)

        hist_hourly_rate = (hist_tot_txns / (24.0 * hist_act_days)).rename("hist_hourly_txn_rate")
        hist_daily_rate = (hist_tot_txns / hist_act_days).rename("hist_daily_txn_rate")
        hist_daily_amt = (hist_tot_amt / hist_act_days).rename("hist_daily_amt_rate")
        hist_avg_amt = (hist_tot_amt / hist_tot_txns.clip(lower=1)).rename("hist_avg_amt")
    else:
        hist_hourly_rate = pd.Series(dtype=float)
        hist_daily_rate = pd.Series(dtype=float)
        hist_daily_amt = pd.Series(dtype=float)
        hist_avg_amt = pd.Series(dtype=float)

    # Current Window Metrics (1h & 24h)
    w1 = txns[txns["in_1h"]]
    cnt_1h = w1.groupby("account_id").size().rename("cnt_1h")

    w24 = txns[txns["in_24h"]]
    cnt_24h = w24.groupby("account_id").size().rename("cnt_24h")
    amt_24h = w24.groupby("account_id")["amount"].sum().rename("amt_24h")
    avg_amt_24h = w24.groupby("account_id")["amount"].mean().rename("avg_amt_24h")

    # Overall fallbacks for new accounts with no prior history
    overall_tot_txns = grp.size()
    overall_tot_amt = grp["amount"].sum()
    overall_days = grp["date"].nunique().clip(lower=1)
    overall_hours = grp["hour"].nunique().clip(lower=1)

    fallback_hourly_rate = (overall_tot_txns / (24.0 * overall_days)).rename("fallback_hourly_rate")
    fallback_daily_rate = (overall_tot_txns / overall_days).rename("fallback_daily_rate")
    fallback_daily_amt = (overall_tot_amt / overall_days).rename("fallback_daily_amt")
    fallback_avg_amt = (overall_tot_amt / overall_tot_txns.clip(lower=1)).rename("fallback_avg_amt")

    # Merge Metrics
    base = pd.DataFrame(index=pd.Index(all_accounts, name="account_id"))
    m = (
        base
        .join(hist_hourly_rate)
        .join(hist_daily_rate)
        .join(hist_daily_amt)
        .join(hist_avg_amt)
        .join(fallback_hourly_rate)
        .join(fallback_daily_rate)
        .join(fallback_daily_amt)
        .join(fallback_avg_amt)
        .join(cnt_1h)
        .join(cnt_24h)
        .join(amt_24h)
        .join(avg_amt_24h)
        .fillna(0.0)
    )

    # Fill 0 historical baselines with fallback values
    m["hist_hourly_txn_rate"] = np.where(m["hist_hourly_txn_rate"] > 0, m["hist_hourly_txn_rate"], m["fallback_hourly_rate"])
    m["hist_daily_txn_rate"] = np.where(m["hist_daily_txn_rate"] > 0, m["hist_daily_txn_rate"], m["fallback_daily_rate"])
    m["hist_daily_amt_rate"] = np.where(m["hist_daily_amt_rate"] > 0, m["hist_daily_amt_rate"], m["fallback_daily_amt"])
    m["hist_avg_amt"] = np.where(m["hist_avg_amt"] > 0, m["hist_avg_amt"], m["fallback_avg_amt"])

    # 3. Calculate Behavior-Change Metrics
    # A. current_1h_vs_historical_ratio
    m["current_1h_vs_historical_ratio"] = (
        m["cnt_1h"] / (m["hist_hourly_txn_rate"] + _EPS)
    ).round(4)

    # B. current_24h_vs_historical_ratio
    m["current_24h_vs_historical_ratio"] = (
        m["cnt_24h"] / (m["hist_daily_txn_rate"] + _EPS)
    ).round(4)

    # C. current_amount_vs_historical_ratio
    m["current_amount_vs_historical_ratio"] = (
        m["amt_24h"] / (m["hist_daily_amt_rate"] + _EPS)
    ).round(4)

    # D. transaction_frequency_change (Difference between 1h count and baseline hourly count)
    m["transaction_frequency_change"] = (
        m["cnt_1h"] - m["hist_hourly_txn_rate"]
    ).round(4)

    # E. average_amount_change (Ratio of recent 24h avg amount vs historical avg amount)
    m["average_amount_change"] = (
        m["avg_amt_24h"] / (m["hist_avg_amt"] + _EPS)
    ).round(4)

    # F. activity_spike_score (Composite score blending frequency and volume acceleration)
    # Scaled from 0.0 to 10.0+
    m["activity_spike_score"] = (
        0.5 * np.minimum(5.0, m["current_1h_vs_historical_ratio"])
        + 0.5 * np.minimum(5.0, m["current_amount_vs_historical_ratio"])
    ).round(4)

    # G. velocity_change_score (Normalized velocity acceleration Z-score)
    mean_ratio = m["current_1h_vs_historical_ratio"].mean()
    std_ratio = m["current_1h_vs_historical_ratio"].std() + _EPS
    m["velocity_change_score"] = (
        (m["current_1h_vs_historical_ratio"] - mean_ratio) / std_ratio
    ).round(4)

    result_df = m.reset_index()
    out_cols = ["account_id"] + TEMPORAL_CHANGE_COLUMNS
    return result_df[out_cols]


def generate_behavioral_shift_visualization(
    output_path: Union[str, pathlib.Path] = pathlib.Path(__file__).parent.parent / "data" / "eda_charts" / "07_temporal_behavioral_shifts.png",
) -> pathlib.Path:
    """
    Generate a visualization comparing Normal Account Behavior vs. Sudden Mule Behavioral Shift.
    """
    output_path = pathlib.Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Synthetic Timeline: 48 hours
    hours = np.arange(1, 49)

    # 1. Normal Account Behavior: Low, steady consumer transactions (1-2 txns/day, small amounts)
    np.random.seed(42)
    normal_txns = np.random.poisson(lam=0.3, size=48)
    normal_amounts = normal_txns * np.random.uniform(50, 200, size=48)

    # 2. Sudden Mule Behavioral Shift: Low baseline for 36 hours -> Massive burst in hours 37-44
    mule_txns = np.random.poisson(lam=0.2, size=48)
    mule_amounts = mule_txns * np.random.uniform(50, 150, size=48)

    # Inject sudden mule burst (hours 37 to 44)
    mule_txns[36:44] = [8, 14, 19, 12, 16, 10, 7, 5]
    mule_amounts[36:44] = [85000, 140000, 220000, 180000, 160000, 95000, 70000, 45000]

    plt.style.use("dark_background")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True)

    # Top Plot: Transaction Counts
    ax1.plot(hours[:36], normal_txns[:36], color="#00E676", label="Normal Account (Baseline)", linewidth=1.8)
    ax1.plot(hours[35:], normal_txns[35:], color="#00E676", linewidth=1.8)

    ax1.plot(hours[:36], mule_txns[:36], color="#29B6F6", label="Mule Account (Baseline)", linewidth=1.8)
    ax1.plot(hours[35:44], mule_txns[35:44], color="#FF1744", linewidth=2.5, label="Sudden Behavioral Shift (Burst)")
    ax1.plot(hours[43:], mule_txns[43:], color="#FF1744", linewidth=1.8)

    ax1.set_ylabel("Txn Count per Hour", fontsize=10)
    ax1.set_title("A. Transaction Frequency Burst (Sudden Shift Detection)", fontsize=11, fontweight="bold")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.2)

    # Bottom Plot: Monetary Amounts
    ax2.plot(hours, normal_amounts, color="#00E676", linewidth=1.8, label="Normal Volume (₹)")
    ax2.plot(hours[:36], mule_amounts[:36], color="#29B6F6", linewidth=1.8, label="Mule Volume (₹ Baseline)")
    ax2.plot(hours[35:44], mule_amounts[35:44], color="#FF1744", linewidth=2.5, label="Mule Monetary Volume Spike")
    ax2.plot(hours[43:], mule_amounts[43:], color="#FF1744", linewidth=1.8)

    ax2.set_xlabel("Timeline (Hours 1 to 48)", fontsize=10)
    ax2.set_ylabel("Total Amount (₹)", fontsize=10)
    ax2.set_title("B. Monetary Volume Spike (Activity Spike Score >> Baseline)", fontsize=11, fontweight="bold")
    ax2.legend(loc="upper left")
    ax2.grid(True, alpha=0.2)

    plt.suptitle("Temporal Behavior-Change Detection: Baseline vs. Mule Burst", fontsize=13, fontweight="bold", y=0.98)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

    logger.info("[TemporalChange] Saved behavioral shift chart -> '%s'", output_path)
    return output_path
