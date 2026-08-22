"""
app/services/features_behavioral.py
-------------------------------------
Behavioral feature computation per account_id.

Output columns (exactly as per docs/feature_schema.md):
  ratio_received_to_sent_24h,
  avg_time_to_forward_funds_minutes,
  unique_counterparty_count,
  account_age_days,
  is_new_high_volume_flag
"""
from __future__ import annotations

import pandas as pd

_EPS = 1e-9

# An account with fewer than this many 7-day transactions is NOT high volume
HIGH_VOLUME_TXN_THRESHOLD = 10

# An account younger than this many days is considered "new"
NEW_ACCOUNT_AGE_DAYS = 30

BEHAVIORAL_COLUMNS: list[str] = [
    "ratio_received_to_sent_24h",
    "avg_time_to_forward_funds_minutes",
    "unique_counterparty_count",
    "account_age_days",
    "is_new_high_volume_flag",
]


def compute_behavioral_features(
    df: pd.DataFrame,
    high_volume_threshold: int = HIGH_VOLUME_TXN_THRESHOLD,
    new_account_age_days: int = NEW_ACCOUNT_AGE_DAYS,
) -> pd.DataFrame:
    """
    Compute behavioral features for every account.

    Parameters
    ----------
    df : pd.DataFrame
        Transaction DataFrame as returned by ``load_transactions``.
    high_volume_threshold : int
        Minimum 7-day txn count to classify an account as high-volume.
    new_account_age_days : int
        Maximum age in days for an account to be considered "new".

    Returns
    -------
    pd.DataFrame
        Columns: ``account_id`` + BEHAVIORAL_COLUMNS.
        All columns are non-null; floats default to 0.0, ints to 0.
    """
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    t_ref: pd.Timestamp = df["timestamp"].max()

    # ------------------------------------------------------------------
    # 24-h window masks on directional views
    # ------------------------------------------------------------------
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
    txns["in_24h"] = delta <= pd.Timedelta(hours=24)
    txns["in_7d"]  = delta <= pd.Timedelta(days=7)

    # ------------------------------------------------------------------
    # 1. ratio_received_to_sent_24h
    #    = total_in_24h / (total_out_24h + eps)
    # ------------------------------------------------------------------
    w24 = txns[txns["in_24h"]]

    in_24h  = (
        w24[w24["direction"] == "in"]
        .groupby("account_id")["amount"].sum()
        .rename("in_24h")
    )
    out_24h = (
        w24[w24["direction"] == "out"]
        .groupby("account_id")["amount"].sum()
        .rename("out_24h")
    )

    ratio_df = pd.concat([in_24h, out_24h], axis=1).fillna(0.0)
    ratio_df["ratio_received_to_sent_24h"] = (
        ratio_df["in_24h"] / (ratio_df["out_24h"] + _EPS)
    )

    # ------------------------------------------------------------------
    # 2. avg_time_to_forward_funds_minutes
    #    For each account: match each inbound txn to the next outbound
    #    txn and record the elapsed minutes. Average those gaps.
    # ------------------------------------------------------------------
    def _avg_forward_minutes(account: str) -> float:
        acc_txns = txns[txns["account_id"] == account].sort_values("timestamp")
        inbound  = acc_txns[acc_txns["direction"] == "in"]["timestamp"].reset_index(drop=True)
        outbound = acc_txns[acc_txns["direction"] == "out"]["timestamp"].reset_index(drop=True)

        if inbound.empty or outbound.empty:
            return 0.0

        gaps: list[float] = []
        for in_ts in inbound:
            # Find the first outbound that comes *after* this inbound
            later = outbound[outbound > in_ts]
            if later.empty:
                continue
            gap_min = (later.iloc[0] - in_ts).total_seconds() / 60.0
            gaps.append(gap_min)

        return float(sum(gaps) / len(gaps)) if gaps else 0.0

    all_accounts = list(txns["account_id"].unique())
    forward_times = pd.Series(
        {acc: _avg_forward_minutes(acc) for acc in all_accounts},
        name="avg_time_to_forward_funds_minutes",
        dtype=float,
    )
    forward_times.index.name = "account_id"

    # ------------------------------------------------------------------
    # 3. unique_counterparty_count  (look-back: all time)
    # ------------------------------------------------------------------
    unique_cp = (
        txns.groupby("account_id")["counterparty"]
        .nunique()
        .rename("unique_counterparty_count")
    )

    # ------------------------------------------------------------------
    # 4. account_age_days
    #    Earliest timestamp the account appears anywhere → age relative to t_ref
    # ------------------------------------------------------------------
    first_seen = (
        txns.groupby("account_id")["timestamp"]
        .min()
    )
    account_age_days = (
        ((t_ref - first_seen).dt.total_seconds() / 86_400)
        .apply(lambda x: max(int(x), 0))
        .rename("account_age_days")
    )

    # ------------------------------------------------------------------
    # 5. is_new_high_volume_flag
    #    1 if age < new_account_age_days AND txn_count_7d > threshold
    # ------------------------------------------------------------------
    txn_count_7d = (
        txns[txns["in_7d"]]
        .groupby("account_id")
        .size()
        .rename("txn_count_7d")
    )

    flag_df = pd.concat(
        [account_age_days, txn_count_7d], axis=1
    ).fillna(0)
    flag_df["txn_count_7d"] = flag_df["txn_count_7d"].astype(int)
    flag_df["is_new_high_volume_flag"] = (
        (flag_df["account_age_days"] < new_account_age_days)
        & (flag_df["txn_count_7d"] > high_volume_threshold)
    ).astype(int)

    # ------------------------------------------------------------------
    # Assemble
    # ------------------------------------------------------------------
    result = (
        pd.DataFrame(index=pd.Index(all_accounts, name="account_id"))
        .join(ratio_df[["ratio_received_to_sent_24h"]])
        .join(forward_times)
        .join(unique_cp)
        .join(account_age_days)
        .join(flag_df[["is_new_high_volume_flag"]])
        .fillna(0)
        .reset_index()
    )

    # Type enforcement per schema contract
    float_cols = ["ratio_received_to_sent_24h", "avg_time_to_forward_funds_minutes"]
    int_cols   = ["unique_counterparty_count", "account_age_days", "is_new_high_volume_flag"]

    result[float_cols] = result[float_cols].astype(float)
    result[int_cols]   = result[int_cols].astype(int)

    return result[["account_id"] + BEHAVIORAL_COLUMNS]
