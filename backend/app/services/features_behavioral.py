"""
app/services/features_behavioral.py
-------------------------------------
Extended Behavioral Feature Computation per account_id.

Output columns:
  - Counterparty Diversity:
      unique_sender_count, unique_receiver_count, unique_counterparty_count
  - Transaction Ratios:
      incoming_transaction_ratio, outgoing_transaction_ratio, ratio_received_to_sent_24h
  - Daily & Temporal Averages:
      average_daily_transaction_count, average_daily_amount, active_days, active_hours
  - Off-Peak / Behavioral Patterns:
      night_transaction_ratio, weekend_transaction_ratio
  - Monetary Dispersion:
      transaction_amount_std, transaction_amount_cv
  - Risk Flags:
      new_account_high_volume_flag (alias: is_new_high_volume_flag), account_age_days
  - Recent vs Historical Ratios:
      recent_vs_historical_transaction_ratio, recent_vs_historical_amount_ratio

Guarantees zero future data leakage (supports as_of_timestamp filtering).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd

_EPS = 1e-9
HIGH_VOLUME_TXN_THRESHOLD = 10
NEW_ACCOUNT_AGE_DAYS = 30

EXTENDED_BEHAVIORAL_COLUMNS: list[str] = [
    "unique_sender_count",
    "unique_receiver_count",
    "unique_counterparty_count",
    "incoming_transaction_ratio",
    "outgoing_transaction_ratio",
    "ratio_received_to_sent_24h",
    "average_daily_transaction_count",
    "average_daily_amount",
    "active_days",
    "active_hours",
    "night_transaction_ratio",
    "weekend_transaction_ratio",
    "transaction_amount_std",
    "transaction_amount_cv",
    "account_age_days",
    "is_new_high_volume_flag",
    "new_account_high_volume_flag",
    "recent_vs_historical_transaction_ratio",
    "recent_vs_historical_amount_ratio",
    "avg_time_to_forward_funds_minutes",
]

# Standard contract list for feature_pipeline.py
BEHAVIORAL_COLUMNS: list[str] = [
    "ratio_received_to_sent_24h",
    "avg_time_to_forward_funds_minutes",
    "unique_counterparty_count",
    "account_age_days",
    "is_new_high_volume_flag",
    "unique_sender_count",
    "unique_receiver_count",
    "incoming_transaction_ratio",
    "outgoing_transaction_ratio",
    "average_daily_transaction_count",
    "average_daily_amount",
    "active_days",
    "active_hours",
    "night_transaction_ratio",
    "weekend_transaction_ratio",
    "transaction_amount_std",
    "transaction_amount_cv",
    "new_account_high_volume_flag",
    "recent_vs_historical_transaction_ratio",
    "recent_vs_historical_amount_ratio",
]


def generate_behavioral_feature_dictionary() -> Dict[str, Dict[str, Any]]:
    """
    Return a structured Feature Dictionary detailing feature definition,
    formula, data type, expected interpretation, and possible mule signal.
    """
    return {
        "unique_sender_count": {
            "definition": "Number of distinct accounts sending funds to this account",
            "formula": "count(distinct sender_id where receiver_id == account_id)",
            "data_type": "int",
            "interpretation": "Higher count indicates multi-source fan-in collection",
            "mule_signal": "High count suggests mule collecting scam proceeds from multiple victims",
        },
        "unique_receiver_count": {
            "definition": "Number of distinct accounts receiving funds from this account",
            "formula": "count(distinct receiver_id where sender_id == account_id)",
            "data_type": "int",
            "interpretation": "Higher count indicates multi-destination fan-out dispersal",
            "mule_signal": "High count suggests mule layering or fanning out funds to secondary mules",
        },
        "unique_counterparty_count": {
            "definition": "Total distinct senders + receivers interacting with this account",
            "formula": "unique_sender_count + unique_receiver_count (distinct union)",
            "data_type": "int",
            "interpretation": "Overall network connectivity footprint",
            "mule_signal": "Sudden expansion in counterparties indicates active fraud ring participation",
        },
        "incoming_transaction_ratio": {
            "definition": "Fraction of total transactions that are incoming deposits",
            "formula": "incoming_count / (total_count + eps)",
            "data_type": "float",
            "interpretation": "0.0 = pure sender, 1.0 = pure recipient",
            "mule_signal": "Extremely high ratio followed by rapid 1.0 outgoing ratio indicates pass-through hub",
        },
        "outgoing_transaction_ratio": {
            "definition": "Fraction of total transactions that are outgoing transfers",
            "formula": "outgoing_count / (total_count + eps)",
            "data_type": "float",
            "interpretation": "0.0 = pure recipient, 1.0 = pure sender",
            "mule_signal": "Extremely high ratio indicates automated or rapid fund draining",
        },
        "average_daily_transaction_count": {
            "definition": "Average number of transactions executed per active day",
            "formula": "total_transaction_count / (active_days + eps)",
            "data_type": "float",
            "interpretation": "Daily transactional frequency per active day",
            "mule_signal": "High frequency bursts on active days signal automated mule bot activity",
        },
        "average_daily_amount": {
            "definition": "Average total monetary amount transacted per active day",
            "formula": "total_amount / (active_days + eps)",
            "data_type": "float",
            "interpretation": "Daily financial velocity",
            "mule_signal": "Abnormally high daily volume relative to account age signals laundering burst",
        },
        "active_days": {
            "definition": "Count of distinct calendar dates on which the account transacted",
            "formula": "count(distinct date(timestamp))",
            "data_type": "int",
            "interpretation": "Temporal spread of account activity",
            "mule_signal": "Low active days with high transaction volume indicates short-lived disposable mule",
        },
        "active_hours": {
            "definition": "Count of distinct hours in the day (0-23) in which account transacted",
            "formula": "count(distinct hour(timestamp))",
            "data_type": "int",
            "interpretation": "Diurnal activity diversity",
            "mule_signal": "24-hour round-the-clock activity indicates script/bot driven automated mules",
        },
        "night_transaction_ratio": {
            "definition": "Fraction of transactions occurring during night hours (11 PM - 5 AM)",
            "formula": "count(txns where hour in [23, 0, 1, 2, 3, 4]) / (total_count + eps)",
            "data_type": "float",
            "interpretation": "Off-peak nocturnal transaction ratio",
            "mule_signal": "High ratio (e.g. > 0.40) indicates covert off-hours laundering to evade monitoring",
        },
        "weekend_transaction_ratio": {
            "definition": "Fraction of transactions occurring on weekends (Saturday/Sunday)",
            "formula": "count(txns where dayofweek >= 5) / (total_count + eps)",
            "data_type": "float",
            "interpretation": "Weekend transaction ratio",
            "mule_signal": "High weekend activity attempts to exploit reduced compliance staffing",
        },
        "transaction_amount_std": {
            "definition": "Standard deviation of transaction amounts for this account",
            "formula": "std(amount)",
            "data_type": "float",
            "interpretation": "Monetary transaction size variance",
            "mule_signal": "Low std on high amounts indicates structured round-number layering transfers",
        },
        "transaction_amount_cv": {
            "definition": "Coefficient of Variation of transaction amounts (std / mean)",
            "formula": "transaction_amount_std / (average_transaction_amount + eps)",
            "data_type": "float",
            "interpretation": "Relative monetary variability",
            "mule_signal": "Extremely low CV (< 0.1) indicates rigid, automated transfer amounts",
        },
        "new_account_high_volume_flag": {
            "definition": "Binary flag indicating a newly created account operating at high volume",
            "formula": "1 if (account_age_days < 30 and txn_count_7d >= 10) else 0",
            "data_type": "int",
            "interpretation": "1 = New high-risk account, 0 = Established or low volume",
            "mule_signal": "Strong indicator of freshly opened 'disposable' mule account",
        },
        "recent_vs_historical_transaction_ratio": {
            "definition": "Ratio of recent 24h transaction count to historical daily average",
            "formula": "txn_count_24h / (average_daily_transaction_count + eps)",
            "data_type": "float",
            "interpretation": "Transaction frequency acceleration ratio",
            "mule_signal": "Ratio >> 1.0 indicates a sudden, suspicious surge in account activity",
        },
        "recent_vs_historical_amount_ratio": {
            "definition": "Ratio of recent 24h monetary volume to historical average daily amount",
            "formula": "amount_24h / (average_daily_amount + eps)",
            "data_type": "float",
            "interpretation": "Monetary volume acceleration ratio",
            "mule_signal": "Ratio >> 1.0 indicates a sudden, suspicious spike in money movement",
        },
    }


def compute_behavioral_features(
    df: pd.DataFrame,
    as_of_timestamp: pd.Timestamp | str | None = None,
    high_volume_threshold: int = HIGH_VOLUME_TXN_THRESHOLD,
    new_account_age_days: int = NEW_ACCOUNT_AGE_DAYS,
) -> pd.DataFrame:
    """
    Compute extended behavioral features for every account.

    Parameters
    ----------
    df : pd.DataFrame
        Transaction DataFrame (must contain: timestamp, sender_account_id,
        receiver_account_id, amount).
    as_of_timestamp : pd.Timestamp | str | None
        Optional point-in-time cutoff. Guarantees zero future data leakage.

    Returns
    -------
    pd.DataFrame
        DataFrame with column ``account_id`` + behavioral feature columns.
    """
    if df.empty:
        return pd.DataFrame(columns=["account_id"] + EXTENDED_BEHAVIORAL_COLUMNS)

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
        return pd.DataFrame(columns=["account_id"] + EXTENDED_BEHAVIORAL_COLUMNS)

    # 2. Build Directional Views (sent and received)
    sent = df[["timestamp", "sender_account_id", "receiver_account_id", "amount"]].rename(
        columns={"sender_account_id": "account_id", "receiver_account_id": "counterparty"}
    )
    sent["direction"] = "out"

    received = df[["timestamp", "receiver_account_id", "sender_account_id", "amount"]].rename(
        columns={"receiver_account_id": "account_id", "sender_account_id": "counterparty"}
    )
    received["direction"] = "in"

    txns = pd.concat([sent, received], ignore_index=True)
    delta = t_ref - txns["timestamp"]

    txns["in_24h"] = (delta >= pd.Timedelta(0)) & (delta <= pd.Timedelta(hours=24))
    txns["in_7d"]  = (delta >= pd.Timedelta(0)) & (delta <= pd.Timedelta(days=7))

    # Extracted Date/Hour attributes
    txns["hour"] = txns["timestamp"].dt.hour
    txns["date"] = txns["timestamp"].dt.date
    txns["dayofweek"] = txns["timestamp"].dt.dayofweek

    txns["is_night"] = txns["hour"].isin([23, 0, 1, 2, 3, 4]).astype(int)
    txns["is_weekend"] = (txns["dayofweek"] >= 5).astype(int)

    all_accounts = sorted(list(txns["account_id"].unique()))

    # 3. Vectorised Group Aggregations
    grp = txns.groupby("account_id")

    # Counterparties
    unique_senders = (
        txns[txns["direction"] == "in"]
        .groupby("account_id")["counterparty"]
        .nunique()
        .rename("unique_sender_count")
    )

    unique_receivers = (
        txns[txns["direction"] == "out"]
        .groupby("account_id")["counterparty"]
        .nunique()
        .rename("unique_receiver_count")
    )

    unique_cp = grp["counterparty"].nunique().rename("unique_counterparty_count")

    # Transaction Ratios
    tot_txns = grp.size().rename("total_count")
    inc_txns = txns[txns["direction"] == "in"].groupby("account_id").size().rename("inc_count")
    out_txns = txns[txns["direction"] == "out"].groupby("account_id").size().rename("out_count")

    # Amounts
    tot_amt = grp["amount"].sum().rename("total_amount")
    amt_std = grp["amount"].std().fillna(0.0).round(4).rename("transaction_amount_std")
    amt_mean = grp["amount"].mean().rename("avg_amt")

    # 24h & 7d windows
    w24 = txns[txns["in_24h"]]
    in_24h = w24[w24["direction"] == "in"].groupby("account_id")["amount"].sum().rename("in_24h")
    out_24h = w24[w24["direction"] == "out"].groupby("account_id")["amount"].sum().rename("out_24h")
    cnt_24h = w24.groupby("account_id").size().rename("cnt_24h")

    w7 = txns[txns["in_7d"]]
    cnt_7d = w7.groupby("account_id").size().rename("cnt_7d")

    # Temporal Diversity
    act_days = grp["date"].nunique().rename("active_days")
    act_hours = grp["hour"].nunique().rename("active_hours")
    night_cnt = grp["is_night"].sum().rename("night_count")
    wnd_cnt = grp["is_weekend"].sum().rename("weekend_count")

    # Account Age
    first_seen = grp["timestamp"].min()
    account_age_days = (
        ((t_ref - first_seen).dt.total_seconds() / 86400.0)
        .apply(lambda x: max(int(x), 0))
        .rename("account_age_days")
    )

    # 4. Assemble Base DataFrame
    base = pd.DataFrame(index=pd.Index(all_accounts, name="account_id"))
    df_merged = (
        base
        .join(unique_senders)
        .join(unique_receivers)
        .join(unique_cp)
        .join(tot_txns)
        .join(inc_txns)
        .join(out_txns)
        .join(tot_amt)
        .join(amt_std)
        .join(amt_mean)
        .join(in_24h)
        .join(out_24h)
        .join(cnt_24h)
        .join(cnt_7d)
        .join(act_days)
        .join(act_hours)
        .join(night_cnt)
        .join(wnd_cnt)
        .join(account_age_days)
        .fillna(0.0)
    )

    # 5. Calculate Ratios & Indicators
    df_merged["unique_sender_count"] = df_merged["unique_sender_count"].astype(int)
    df_merged["unique_receiver_count"] = df_merged["unique_receiver_count"].astype(int)
    df_merged["unique_counterparty_count"] = df_merged["unique_counterparty_count"].astype(int)
    df_merged["active_days"] = df_merged["active_days"].astype(int)
    df_merged["active_hours"] = df_merged["active_hours"].astype(int)
    df_merged["account_age_days"] = df_merged["account_age_days"].astype(int)

    # Transaction Direction Ratios
    df_merged["incoming_transaction_ratio"] = (df_merged["inc_count"] / (df_merged["total_count"] + _EPS)).round(4)
    df_merged["outgoing_transaction_ratio"] = (df_merged["out_count"] / (df_merged["total_count"] + _EPS)).round(4)
    df_merged["ratio_received_to_sent_24h"] = (df_merged["in_24h"] / (df_merged["out_24h"] + _EPS)).round(4)

    # Daily Averages
    df_merged["average_daily_transaction_count"] = (df_merged["total_count"] / (df_merged["active_days"] + _EPS)).round(4)
    df_merged["average_daily_amount"] = (df_merged["total_amount"] / (df_merged["active_days"] + _EPS)).round(4)

    # Off-Peak / Behavioral Ratios
    df_merged["night_transaction_ratio"] = (df_merged["night_count"] / (df_merged["total_count"] + _EPS)).round(4)
    df_merged["weekend_transaction_ratio"] = (df_merged["weekend_count"] / (df_merged["total_count"] + _EPS)).round(4)

    # Monetary Dispersion
    df_merged["transaction_amount_cv"] = (df_merged["transaction_amount_std"] / (df_merged["avg_amt"] + _EPS)).round(4)

    # Risk Flags
    is_new_hv = (
        (df_merged["account_age_days"] < new_account_age_days)
        & (df_merged["cnt_7d"] >= high_volume_threshold)
    ).astype(int)
    df_merged["is_new_high_volume_flag"] = is_new_hv
    df_merged["new_account_high_volume_flag"] = is_new_hv

    # Recent vs Historical Ratios
    df_merged["recent_vs_historical_transaction_ratio"] = (
        df_merged["cnt_24h"] / (df_merged["average_daily_transaction_count"] + _EPS)
    ).round(4)

    amt_24h_tot = df_merged["in_24h"] + df_merged["out_24h"]
    df_merged["recent_vs_historical_amount_ratio"] = (
        amt_24h_tot / (df_merged["average_daily_amount"] + _EPS)
    ).round(4)

    # Calculate avg_time_to_forward_funds_minutes (Vectorised/FIFO matching helper)
    def _calc_forward_time(acc: str) -> float:
        acc_txns = txns[txns["account_id"] == acc].sort_values("timestamp")
        in_ts = acc_txns[acc_txns["direction"] == "in"]["timestamp"].values
        out_ts = acc_txns[acc_txns["direction"] == "out"]["timestamp"].values

        if len(in_ts) == 0 or len(out_ts) == 0:
            return 0.0

        gaps = []
        for t_in in in_ts:
            subsequent = out_ts[out_ts > t_in]
            if len(subsequent) > 0:
                gaps.append((subsequent[0] - t_in) / np.timedelta64(1, "m"))

        return float(np.mean(gaps)) if gaps else 0.0

    fwd_times = pd.Series(
        {acc: _calc_forward_time(acc) for acc in all_accounts},
        name="avg_time_to_forward_funds_minutes",
    ).round(2)

    df_merged = df_merged.join(fwd_times).fillna(0.0).reset_index()

    out_cols = ["account_id"] + [c for c in EXTENDED_BEHAVIORAL_COLUMNS if c in df_merged.columns]
    return df_merged[out_cols]
