"""
scripts/verify_graph_signals.py
---------------------------------
AC2 verification: run both graph and anomaly features on the injected
dataset, then spot-check a handful of known-mule account_ids to confirm
elevated signals (is_in_short_cycle, fan_out_ratio, betweenness_centrality).

Usage:
    python scripts/verify_graph_signals.py \
        --input app/data/mule_injected.csv \
        --n-show 5
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="app/data/mule_injected.csv")
    parser.add_argument("--n-show", type=int, default=5,
                        help="Number of mule accounts to spot-check")
    args = parser.parse_args()

    from app.services.data_loader import load_transactions
    from app.services.features_graph import compute_graph_features
    from app.services.features_anomaly import compute_anomaly_features

    print(f"\n{'='*60}")
    print("  A4 Verification: Graph + Anomaly on full dataset")
    print(f"{'='*60}\n")

    df = load_transactions(args.input)
    print(f"Loaded {len(df):,} rows, {df['is_mule_pattern'].sum():,} mule rows\n")

    # ---- time graph features ----
    t_total = time.perf_counter()
    gf = compute_graph_features(df)
    t_graph = time.perf_counter() - t_total
    print()

    # ---- time anomaly features ----
    t_anom = time.perf_counter()
    af = compute_anomaly_features(df)
    t_anomaly = time.perf_counter() - t_anom

    t_combined = time.perf_counter() - t_total
    print(f"\nGraph:   {t_graph:.2f}s")
    print(f"Anomaly: {t_anomaly:.3f}s")
    print(f"COMBINED: {t_combined:.2f}s  ({'OK < 30s' if t_combined < 30 else 'SLOW > 30s'})\n")

    # ---- spot-check known mule accounts ----
    # Mule accounts are those that sent or received with is_mule_pattern=1
    mule_senders = set(df[df["is_mule_pattern"] == 1]["sender_account_id"].unique())
    sample_mules = list(mule_senders)[:args.n_show]

    merged = gf.merge(af, on="account_id")

    print(f"{'='*60}")
    print(f"  Spot-check: {len(sample_mules)} known-mule account_ids")
    print(f"{'='*60}")
    pd.set_option("display.float_format", "{:.4f}".format)
    pd.set_option("display.max_columns", 20)
    pd.set_option("display.width", 120)

    show_cols = [
        "account_id", "in_degree", "out_degree",
        "is_in_short_cycle", "betweenness_centrality",
        "fan_out_ratio", "amount_zscore_avg",
    ]
    spot = merged[merged["account_id"].isin(sample_mules)][show_cols]
    print(spot.to_string(index=False))

    # Summary stats: mule vs clean
    all_accounts_mule = df[df["is_mule_pattern"] == 1]["sender_account_id"].unique()
    mule_gf  = merged[merged["account_id"].isin(all_accounts_mule)]
    clean_gf = merged[~merged["account_id"].isin(all_accounts_mule)]

    print(f"\n{'='*60}")
    print("  Signal comparison: mule senders vs clean accounts")
    print(f"{'='*60}")
    compare_cols = ["in_degree", "out_degree", "is_in_short_cycle",
                    "betweenness_centrality", "fan_out_ratio", "amount_zscore_avg"]
    print("\nMule senders (mean):")
    print(mule_gf[compare_cols].mean().to_string())
    print("\nClean accounts (mean):")
    print(clean_gf[compare_cols].mean().to_string())


if __name__ == "__main__":
    main()
