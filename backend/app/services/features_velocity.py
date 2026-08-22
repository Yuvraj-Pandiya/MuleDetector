"""
app/services/features_velocity.py
----------------------------------
Velocity feature computation per account_id.

Output columns (exactly as per docs/feature_schema.md):
  txn_count_1h, txn_count_24h, txn_count_7d,
  total_amount_out_24h, total_amount_in_24h,
  avg_transaction_amount, max_transaction_amount
"""
from __future__ import annotations

import pandas as pd

# Epsilon prevents divide-by-zero in downstream ratio features
_EPS = 1e-9

# High-volume threshold used for is_new_high_volume_flag (shared with behavioral)
HIGH_VOLUME_TXN_THRESHOLD = 10

# All output columns in schema-contract order
VELOCITY_COLUMNS: list[str] = [
    "txn_count_1h",
    "txn_count_24h",
    "txn_count_7d",
    "total_amount_out_24h",
    "total_amount_in_24h",
    "avg_transaction_amount",
    "max_transaction_amount",
]


def compute_velocity_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute velocity features for every account that appears as a sender
    or receiver.

    The reference timestamp (``t_ref``) is the **maximum** timestamp in the
    dataset, simulating "as-of-now" in a batch run.

    Parameters
    ----------
    df : pd.DataFrame
        Transaction DataFrame as returned by ``load_transactions``.
        Required columns: timestamp, sender_account_id,
        receiver_account_id, amount.

    Returns
    -------
    pd.DataFrame
        Index: default integer range.
        Columns: ``account_id`` + VELOCITY_COLUMNS.
        All int/float columns are non-null (NaN filled with 0).
    """
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    t_ref: pd.Timestamp = df["timestamp"].max()

    # ------------------------------------------------------------------
    # Build unified view: one row per (account, txn) from BOTH directions
    # ------------------------------------------------------------------
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

    # Time-window masks (relative to reference timestamp)
    delta = (t_ref - txns["timestamp"])
    txns["in_1h"]  = delta <= pd.Timedelta(hours=1)
    txns["in_24h"] = delta <= pd.Timedelta(hours=24)
    txns["in_7d"]  = delta <= pd.Timedelta(days=7)

    # ------------------------------------------------------------------
    # Aggregate per account
    # ------------------------------------------------------------------
    grp = txns.groupby("account_id")

    # Transaction counts within windows (both directions count)
    txn_count_1h  = grp.apply(lambda g: g["in_1h"].sum(), include_groups=False).rename("txn_count_1h")
    txn_count_24h = grp.apply(lambda g: g["in_24h"].sum(), include_groups=False).rename("txn_count_24h")
    txn_count_7d  = grp.apply(lambda g: g["in_7d"].sum(), include_groups=False).rename("txn_count_7d")

    # Directional amount sums within 24 h
    def _amount_out_24h(g: pd.DataFrame) -> float:
        mask = g["in_24h"] & (g["direction"] == "out")
        return float(g.loc[mask, "amount"].sum())

    def _amount_in_24h(g: pd.DataFrame) -> float:
        mask = g["in_24h"] & (g["direction"] == "in")
        return float(g.loc[mask, "amount"].sum())

    total_amount_out_24h = grp.apply(_amount_out_24h, include_groups=False).rename("total_amount_out_24h")
    total_amount_in_24h  = grp.apply(_amount_in_24h,  include_groups=False).rename("total_amount_in_24h")

    # Global avg / max over the entire look-back window (all rows)
    avg_txn_amount = grp["amount"].mean().rename("avg_transaction_amount")
    max_txn_amount = grp["amount"].max().rename("max_transaction_amount")

    # ------------------------------------------------------------------
    # Assemble result DataFrame
    # ------------------------------------------------------------------
    result = pd.concat(
        [
            txn_count_1h,
            txn_count_24h,
            txn_count_7d,
            total_amount_out_24h,
            total_amount_in_24h,
            avg_txn_amount,
            max_txn_amount,
        ],
        axis=1,
    ).reset_index()  # brings account_id out of the index

    # ------------------------------------------------------------------
    # Type enforcement per schema contract
    # ------------------------------------------------------------------
    int_cols = ["txn_count_1h", "txn_count_24h", "txn_count_7d"]
    float_cols = [
        "total_amount_out_24h",
        "total_amount_in_24h",
        "avg_transaction_amount",
        "max_transaction_amount",
    ]

    result[int_cols]   = result[int_cols].fillna(0).astype(int)
    result[float_cols] = result[float_cols].fillna(0.0).astype(float)

    # Guarantee column order
    return result[["account_id"] + VELOCITY_COLUMNS]
