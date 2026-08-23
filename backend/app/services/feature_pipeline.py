"""
app/services/feature_pipeline.py
----------------------------------
Orchestrates all four feature modules into a single merged DataFrame
that matches docs/feature_schema.md exactly.

Public API
----------
build_feature_matrix(csv_path) -> pd.DataFrame

Column contract (schema v0.1.0)
-------------------------------
account_id                        str
-- velocity --
txn_count_1h                      int
txn_count_24h                     int
txn_count_7d                      int
total_amount_out_24h              float
total_amount_in_24h               float
avg_transaction_amount            float
max_transaction_amount            float
-- behavioral --
ratio_received_to_sent_24h        float
avg_time_to_forward_funds_minutes float
unique_counterparty_count         int
account_age_days                  int
is_new_high_volume_flag           int
-- graph --
in_degree                         int
out_degree                        int
is_in_short_cycle                 int
betweenness_centrality            float
fan_in_ratio                      float
fan_out_ratio                     float
-- anomaly --
amount_zscore_avg                 float
round_number_txn_ratio            float
odd_hour_txn_ratio                float
-- label (optional) --
is_mule_pattern                   int  (absent when not in source data)
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Union

import pandas as pd

from app.services.data_loader import load_transactions
from app.services.features_velocity import (
    VELOCITY_COLUMNS,
    compute_velocity_features,
)
from app.services.features_behavioral import (
    BEHAVIORAL_COLUMNS,
    compute_behavioral_features,
)
from app.services.features_graph import (
    GRAPH_COLUMNS,
    compute_graph_features,
)
from app.services.features_anomaly import (
    ANOMALY_COLUMNS,
    compute_anomaly_features,
)

# -------------------------------------------------------------------------
# Canonical column order (matches docs/feature_schema.md)
# -------------------------------------------------------------------------
FEATURE_COLUMNS: list[str] = (
    VELOCITY_COLUMNS
    + BEHAVIORAL_COLUMNS
    + GRAPH_COLUMNS
    + ANOMALY_COLUMNS
)

SCHEMA_COLUMNS: list[str] = ["account_id"] + FEATURE_COLUMNS  # without label


def build_feature_matrix(
    csv_path: Union[str, Path],
    *,
    warn_seconds: float = 60.0,
) -> pd.DataFrame:
    """
    Load raw transactions, compute all feature groups, merge into one
    DataFrame that matches the schema contract exactly.

    Parameters
    ----------
    csv_path : str | Path
        Path to the transaction CSV (as saved by POST /upload-dataset).
    warn_seconds : float
        Print a warning if pipeline takes longer than this many seconds.

    Returns
    -------
    pd.DataFrame
        One row per account_id.  Columns in schema contract order.
        NaN filled with 0.  ``is_mule_pattern`` appended if present
        in the source CSV; absent otherwise.
    """
    t_start = time.perf_counter()

    # ------------------------------------------------------------------
    # 1. Ingest, preprocess & validate
    # ------------------------------------------------------------------
    print("[pipeline] Loading & preprocessing transactions ...")
    from app.services.preprocessing_pipeline import preprocess_transactions
    df, stats, rejected_df = preprocess_transactions(csv_path)
    has_label = "is_mule_pattern" in df.columns
    print(
        f"[pipeline] Cleaned {len(df):,} rows (rejected {len(rejected_df):,}) | "
        f"{df['sender_account_id'].nunique():,} unique senders | "
        f"label present: {has_label}"
    )

    # ------------------------------------------------------------------
    # 2. Compute each feature group
    # ------------------------------------------------------------------
    t1 = time.perf_counter()
    print("[pipeline] Computing velocity features ...")
    vf = compute_velocity_features(df)
    print(f"[pipeline]   velocity   -> {time.perf_counter() - t1:.2f}s")

    t2 = time.perf_counter()
    print("[pipeline] Computing behavioral features ...")
    bf = compute_behavioral_features(df)
    print(f"[pipeline]   behavioral -> {time.perf_counter() - t2:.2f}s")

    t3 = time.perf_counter()
    print("[pipeline] Computing graph features ...")
    gf = compute_graph_features(df)
    print(f"[pipeline]   graph      -> {time.perf_counter() - t3:.2f}s")

    t4 = time.perf_counter()
    print("[pipeline] Computing anomaly features ...")
    af = compute_anomaly_features(df)
    print(f"[pipeline]   anomaly    -> {time.perf_counter() - t4:.2f}s")

    # ------------------------------------------------------------------
    # 3. Merge on account_id (outer join to keep every account)
    # ------------------------------------------------------------------
    print("[pipeline] Merging feature groups ...")
    merged = (
        vf
        .merge(bf, on="account_id", how="outer")
        .merge(gf, on="account_id", how="outer")
        .merge(af, on="account_id", how="outer")
    )

    # ------------------------------------------------------------------
    # 4. Fill NaN with 0 (schema constraint: no nulls allowed)
    # ------------------------------------------------------------------
    merged = merged.fillna(0)

    # ------------------------------------------------------------------
    # 5. Attach label if present in source data
    # ------------------------------------------------------------------
    if has_label:
        # Label propagation: only accounts that SENT flagged transactions are
        # labelled as mules. Receivers are NOT propagated because they may be
        # victims receiving money from a mule, not mules themselves.
        # Mule pattern label is on the transaction row; a sender account is
        # a mule if ANY transaction they sent carries is_mule_pattern == 1.
        label_map = (
            df.groupby("sender_account_id")["is_mule_pattern"]
            .max()
            .reset_index()
            .rename(columns={"sender_account_id": "account_id"})
        )
        merged = merged.merge(label_map, on="account_id", how="left")
        merged["is_mule_pattern"] = (
            merged["is_mule_pattern"].fillna(0).astype(int)
        )

    # ------------------------------------------------------------------
    # 6. Enforce final column order
    # ------------------------------------------------------------------
    final_cols = SCHEMA_COLUMNS.copy()
    if has_label:
        final_cols.append("is_mule_pattern")

    # Safety: add any missing columns as 0 (shouldn't happen, but guards Track B)
    for col in final_cols:
        if col not in merged.columns:
            merged[col] = 0

    merged = merged[final_cols].reset_index(drop=True)

    # ------------------------------------------------------------------
    # 7. Type enforcement (int vs float per schema)
    # ------------------------------------------------------------------
    int_schema = [
        "txn_count_1h", "txn_count_24h", "txn_count_7d",
        "unique_counterparty_count", "account_age_days", "is_new_high_volume_flag",
        "in_degree", "out_degree", "is_in_short_cycle",
    ]
    if has_label:
        int_schema.append("is_mule_pattern")

    float_schema = [c for c in final_cols if c not in int_schema and c != "account_id"]

    merged[int_schema]   = merged[int_schema].astype(int)
    merged[float_schema] = merged[float_schema].astype(float)

    # ------------------------------------------------------------------
    # 8. Timing report
    # ------------------------------------------------------------------
    elapsed = time.perf_counter() - t_start
    status  = "OK" if elapsed < warn_seconds else f"WARNING: exceeded {warn_seconds}s limit"
    print(
        f"\n[pipeline] Done: {len(merged):,} accounts | "
        f"{len(final_cols)} columns | "
        f"elapsed: {elapsed:.2f}s [{status}]"
    )

    return merged
