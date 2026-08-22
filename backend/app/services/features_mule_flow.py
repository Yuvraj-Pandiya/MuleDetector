"""
app/services/features_mule_flow.py
===================================
Mule Fund-Flow Feature Module for MuleDetector.

Purpose:
Detect rapid pass-through behavior commonly associated with money mule activity
(e.g., receiving funds and immediately forwarding them to another destination).

Matching Strategy & Causal Inference Rules:
--------------------------------------------
For each incoming transaction T_in (at timestamp t_in with amount A_in) for account A:
  1. We identify the first subsequent outgoing transaction T_out (at timestamp t_out)
     where t_out >= t_in.
  2. If t_out < t_in (outgoing transaction occurred BEFORE incoming funds arrived),
     it is NEVER matched or inferred to be caused by T_in.
  3. Delay (minutes) = (t_out - t_in).total_seconds() / 60.0.
  4. If an account has no subsequent outgoing transactions after T_in,
     it is treated as non-forwarded (default high retention).
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_EPS = 1e-9

MULE_FLOW_COLUMNS: list[str] = [
    "avg_time_to_forward_funds",
    "median_time_to_forward_funds",
    "min_time_to_forward_funds",
    "pct_funds_forwarded_within_5min",
    "pct_funds_forwarded_within_15min",
    "pct_funds_forwarded_within_1hour",
    "incoming_to_outgoing_amount_ratio",
    "outgoing_to_incoming_amount_ratio",
    "fund_retention_ratio",
    "same_day_fund_forwarding_ratio",
]


def compute_mule_flow_features(
    df: pd.DataFrame,
    as_of_timestamp: pd.Timestamp | str | None = None,
) -> pd.DataFrame:
    """
    Compute mule fund-flow pass-through features for every account.

    Parameters
    ----------
    df : pd.DataFrame
        Transaction DataFrame (must contain: timestamp, sender_account_id,
        receiver_account_id, amount).
    as_of_timestamp : pd.Timestamp | str | None
        Optional point-in-time cutoff. Excludes transactions after this timestamp.

    Returns
    -------
    pd.DataFrame
        DataFrame with column ``account_id`` + MULE_FLOW_COLUMNS.
    """
    if df.empty:
        return pd.DataFrame(columns=["account_id"] + MULE_FLOW_COLUMNS)

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    # Point-in-Time Causality Cutoff
    if as_of_timestamp is not None:
        t_ref = pd.to_datetime(as_of_timestamp)
        df = df[df["timestamp"] <= t_ref].copy()

    if df.empty:
        return pd.DataFrame(columns=["account_id"] + MULE_FLOW_COLUMNS)

    # Sort chronologically
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Identify all unique accounts
    all_senders = set(df["sender_account_id"].astype(str))
    all_receivers = set(df["receiver_account_id"].astype(str))
    all_accounts = sorted(list(all_senders.union(all_receivers)))

    # Separate incoming and outgoing transactions per account
    # Group incoming by receiver_account_id
    inc_grp = df.groupby("receiver_account_id")
    # Group outgoing by sender_account_id
    out_grp = df.groupby("sender_account_id")

    inc_dict = {str(k): v for k, v in inc_grp}
    out_dict = {str(k): v for k, v in out_grp}

    records = []

    for acc in all_accounts:
        inc_txns = inc_dict.get(acc, pd.DataFrame())
        out_txns = out_dict.get(acc, pd.DataFrame())

        tot_inc_amt = float(inc_txns["amount"].sum()) if not inc_txns.empty else 0.0
        tot_out_amt = float(out_txns["amount"].sum()) if not out_txns.empty else 0.0

        # Amount Ratios
        inc_to_out_ratio = round(tot_inc_amt / (tot_out_amt + _EPS), 4)
        out_to_inc_ratio = round(tot_out_amt / (tot_inc_amt + _EPS), 4)

        # Fund Retention Ratio: (Inflow - Outflow) / (Inflow + eps), clipped >= 0
        retention_ratio = round(max(0.0, (tot_inc_amt - tot_out_amt) / (tot_inc_amt + _EPS)), 4)

        # Matching Logic for Forwarding Delays
        # Default placeholders for accounts with no pass-through/forwarding
        delays_minutes = []
        forwarded_amounts = []
        same_day_flags = []

        if not inc_txns.empty and not out_txns.empty:
            out_times = out_txns["timestamp"].values

            for _, inc_row in inc_txns.iterrows():
                t_in = inc_row["timestamp"]
                a_in = float(inc_row["amount"])

                # Causal Rule: find subsequent outgoing transactions where t_out >= t_in
                subsequent_mask = out_times >= t_in.to_datetime64()
                if np.any(subsequent_mask):
                    # First subsequent outgoing transaction
                    t_out = pd.Timestamp(out_times[subsequent_mask][0])
                    delay_min = (t_out - t_in).total_seconds() / 60.0

                    delays_minutes.append(delay_min)
                    forwarded_amounts.append(a_in)

                    # Same day forwarding flag (within 24 hours / same calendar day)
                    same_day_flags.append(1 if delay_min <= 1440.0 else 0)

        # Calculate Delay Statistics
        if delays_minutes:
            avg_delay = round(float(np.mean(delays_minutes)), 2)
            median_delay = round(float(np.median(delays_minutes)), 2)
            min_delay = round(float(np.min(delays_minutes)), 2)

            total_fwd_vol = sum(forwarded_amounts) + _EPS
            vol_5m = sum(a for a, d in zip(forwarded_amounts, delays_minutes) if d <= 5.0)
            vol_15m = sum(a for a, d in zip(forwarded_amounts, delays_minutes) if d <= 15.0)
            vol_1h = sum(a for a, d in zip(forwarded_amounts, delays_minutes) if d <= 60.0)

            pct_5m = round(vol_5m / total_fwd_vol, 4)
            pct_15m = round(vol_15m / total_fwd_vol, 4)
            pct_1h = round(vol_1h / total_fwd_vol, 4)
            same_day_ratio = round(sum(same_day_flags) / max(len(same_day_flags), 1), 4)
        else:
            # Safe default for accounts with no forwarded transactions (e.g. 1440.0 min default delay)
            avg_delay = 1440.0
            median_delay = 1440.0
            min_delay = 1440.0
            pct_5m = 0.0
            pct_15m = 0.0
            pct_1h = 0.0
            same_day_ratio = 0.0

        records.append({
            "account_id": acc,
            "avg_time_to_forward_funds": avg_delay,
            "median_time_to_forward_funds": median_delay,
            "min_time_to_forward_funds": min_delay,
            "pct_funds_forwarded_within_5min": pct_5m,
            "pct_funds_forwarded_within_15min": pct_15m,
            "pct_funds_forwarded_within_1hour": pct_1h,
            "incoming_to_outgoing_amount_ratio": inc_to_out_ratio,
            "outgoing_to_incoming_amount_ratio": out_to_inc_ratio,
            "fund_retention_ratio": retention_ratio,
            "same_day_fund_forwarding_ratio": same_day_ratio,
        })

    result_df = pd.DataFrame(records, columns=["account_id"] + MULE_FLOW_COLUMNS)
    return result_df
