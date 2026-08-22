"""
scripts/generate_mock_features.py
==================================
Generate a synthetic feature matrix CSV at app/data/mock_features.csv
conforming exactly to docs/feature_schema.md (23 columns, 1 000 rows).

~5 % of rows are labeled is_mule_pattern=1 and have feature values that
plausibly correlate with mule-account behaviour so that a model trained
on this data learns real signal rather than pure noise.

Usage:
    python scripts/generate_mock_features.py

Output:
    app/data/mock_features.csv
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
N_ROWS: int = 1_000
MULE_RATE: float = 0.05          # ~5 % positive-label rate
RANDOM_SEED: int = 42
OUTPUT_PATH: pathlib.Path = pathlib.Path(__file__).parent.parent / "app" / "data" / "mock_features.csv"

# Column order exactly as declared in docs/feature_schema.md
SCHEMA_COLUMNS: list[str] = [
    # Key
    "account_id",
    # Velocity
    "txn_count_1h",
    "txn_count_24h",
    "txn_count_7d",
    "total_amount_out_24h",
    "total_amount_in_24h",
    "avg_transaction_amount",
    "max_transaction_amount",
    # Behavioral
    "ratio_received_to_sent_24h",
    "avg_time_to_forward_funds_minutes",
    "unique_counterparty_count",
    "account_age_days",
    "is_new_high_volume_flag",
    # Graph
    "in_degree",
    "out_degree",
    "is_in_short_cycle",
    "betweenness_centrality",
    "fan_in_ratio",
    "fan_out_ratio",
    # Anomaly
    "amount_zscore_avg",
    "round_number_txn_ratio",
    "odd_hour_txn_ratio",
    # Label
    "is_mule_pattern",
]

EPS: float = 1e-6   # small epsilon used in ratio denominators


# ---------------------------------------------------------------------------
# Helper generators
# ---------------------------------------------------------------------------

def _generate_benign(rng: np.random.Generator, n: int) -> dict[str, np.ndarray]:
    """Return feature arrays for n benign (label=0) accounts.

    Distributions intentionally overlap with mule distributions on every
    feature so that no single split achieves perfect separation.  The model
    must learn a *combination* of features, which produces realistic
    sub-100 % metrics.
    """

    txn_count_1h      = rng.integers(0,   8,    size=n)   # low burst (0-7 vs 2-15 mule)
    txn_count_24h     = rng.integers(1,   50,   size=n)   # overlaps mule 10-80
    txn_count_7d      = rng.integers(5,   200,  size=n)   # overlaps mule 30-350

    total_amount_out  = rng.uniform(50,   8_000,  size=n).round(2)
    total_amount_in   = rng.uniform(50,   8_000,  size=n).round(2)
    avg_txn_amount    = rng.uniform(20,   800,    size=n).round(2)
    max_txn_amount    = (avg_txn_amount + rng.uniform(0, 800, size=n)).round(2)

    # Benign: ratio near 1, but can occasionally be higher
    ratio_recv_sent   = (total_amount_in / (total_amount_out + EPS)).round(4)

    # KEY — was 60–2880 (no overlap). Now 30–1440: overlaps mule 15–300
    avg_fwd_minutes   = rng.uniform(30, 1_440, size=n).round(2)

    unique_cp         = rng.integers(1,  40,  size=n)     # overlaps mule 3-50
    account_age_days  = rng.integers(20, 3_650, size=n)   # overlaps mule 5-365

    is_new_high_vol   = ((account_age_days < 30) & (txn_count_7d > 50)).astype(int)

    # KEY — was 1–20 (no overlap with mule 15–60). Now 1–40: overlaps well
    in_degree         = rng.integers(1, 25, size=n)
    out_degree        = rng.integers(1, 35, size=n)       # overlaps mule 10-50
    total_degree      = in_degree + out_degree + EPS
    is_short_cycle    = rng.choice([0, 1], size=n, p=[0.88, 0.12])  # slight overlap
    betweenness       = rng.uniform(0.0, 0.15, size=n).round(6)     # overlaps mule 0.02-0.25
    fan_in_ratio      = (in_degree  / total_degree).round(4)
    fan_out_ratio     = (out_degree / total_degree).round(4)

    # KEY — was normal(0, 0.8) vs normal(2, 1): barely overlapping tails.
    # Now benign ~N(0.3, 1.0), mule ~N(1.5, 1.0) — substantial overlap
    amount_zscore     = rng.normal(0.3, 1.0, size=n).round(4)
    round_num_ratio   = rng.uniform(0.05, 0.50, size=n).round(4)  # overlaps mule 0.25-0.80
    # KEY — was 0.02-0.20 (no overlap with mule 0.30-0.80). Now 0.02-0.45
    odd_hour_ratio    = rng.uniform(0.02, 0.45, size=n).round(4)

    return {
        "txn_count_1h":                      txn_count_1h,
        "txn_count_24h":                     txn_count_24h,
        "txn_count_7d":                      txn_count_7d,
        "total_amount_out_24h":              total_amount_out,
        "total_amount_in_24h":              total_amount_in,
        "avg_transaction_amount":            avg_txn_amount,
        "max_transaction_amount":            max_txn_amount,
        "ratio_received_to_sent_24h":        ratio_recv_sent,
        "avg_time_to_forward_funds_minutes": avg_fwd_minutes,
        "unique_counterparty_count":         unique_cp,
        "account_age_days":                  account_age_days,
        "is_new_high_volume_flag":           is_new_high_vol,
        "in_degree":                         in_degree,
        "out_degree":                        out_degree,
        "is_in_short_cycle":                 is_short_cycle,
        "betweenness_centrality":            betweenness,
        "fan_in_ratio":                      fan_in_ratio,
        "fan_out_ratio":                     fan_out_ratio,
        "amount_zscore_avg":                 amount_zscore,
        "round_number_txn_ratio":            round_num_ratio,
        "odd_hour_txn_ratio":                odd_hour_ratio,
    }


def _generate_mule(rng: np.random.Generator, n: int) -> dict[str, np.ndarray]:
    """Return feature arrays for n mule (label=1) accounts.

    Mule signal is encoded through higher *means* on risk features, but with
    enough variance that distributions overlap with benign, forcing the model
    to learn a multi-feature boundary rather than a single perfect split.

    - Low avg_time_to_forward_funds_minutes  (rapid pass-through)
    - High fan_out_ratio / out_degree        (many outbound counterparties)
    - High ratio_received_to_sent_24h        (receive then forward everything)
    - Higher txn_count_24h / txn_count_1h    (burst activity)
    - Younger accounts (lower account_age_days)
    - More likely to be in a short cycle
    - Higher betweenness centrality
    - Higher odd_hour_txn_ratio
    """

    # Overlaps benign 0–8; mules skew high but some benign accounts also burst
    txn_count_1h      = rng.integers(2,  15,   size=n)
    txn_count_24h     = rng.integers(10, 80,   size=n)   # overlaps benign 1-50
    txn_count_7d      = rng.integers(30, 350,  size=n)   # overlaps benign 5-200

    total_amount_out  = rng.uniform(200,  15_000, size=n).round(2)
    # Mules receive more than they send — but ratio isn't always extreme
    total_amount_in   = (total_amount_out * rng.uniform(1.1, 2.5, size=n)).round(2)
    avg_txn_amount    = rng.uniform(100,  2_000,  size=n).round(2)
    max_txn_amount    = (avg_txn_amount  + rng.uniform(200, 4_000, size=n)).round(2)

    ratio_recv_sent   = (total_amount_in / (total_amount_out + EPS)).round(4)

    # KEY SIGNAL — rapid forwarding, but with wide variance so some mules look slow
    # Overlaps benign 30-1440; mule distribution peaks lower (15-300)
    avg_fwd_minutes   = rng.uniform(5, 300, size=n).round(2)

    unique_cp         = rng.integers(3, 50, size=n)      # overlaps benign 1-40
    account_age_days  = rng.integers(5, 365, size=n)     # overlaps benign 20-3650

    is_new_high_vol   = ((account_age_days < 30) & (txn_count_7d > 50)).astype(int)

    # KEY SIGNAL — higher out_degree on average, but overlaps benign
    in_degree         = rng.integers(2, 20, size=n)       # overlaps benign
    out_degree        = rng.integers(10, 50, size=n)      # overlaps benign 1-35
    total_degree      = in_degree + out_degree + EPS
    is_short_cycle    = rng.choice([0, 1], size=n, p=[0.55, 0.45])  # higher but not always
    betweenness       = rng.uniform(0.02, 0.25, size=n).round(6)    # overlaps benign 0-0.15
    fan_in_ratio      = (in_degree  / total_degree).round(4)
    fan_out_ratio     = (out_degree / total_degree).round(4)

    # KEY SIGNAL — mules skew higher but wide std means real overlap
    # benign ~N(0.3, 1.0)  vs  mule ~N(1.5, 1.0): ~15% overlap in tails
    amount_zscore     = rng.normal(1.5, 1.0, size=n).round(4)
    round_num_ratio   = rng.uniform(0.25, 0.80, size=n).round(4)  # overlaps benign 0.05-0.50
    # KEY SIGNAL — overlaps benign 0.02-0.45; mule skews 0.20-0.75
    odd_hour_ratio    = rng.uniform(0.20, 0.75, size=n).round(4)

    return {
        "txn_count_1h":                      txn_count_1h,
        "txn_count_24h":                     txn_count_24h,
        "txn_count_7d":                      txn_count_7d,
        "total_amount_out_24h":              total_amount_out,
        "total_amount_in_24h":              total_amount_in,
        "avg_transaction_amount":            avg_txn_amount,
        "max_transaction_amount":            max_txn_amount,
        "ratio_received_to_sent_24h":        ratio_recv_sent,
        "avg_time_to_forward_funds_minutes": avg_fwd_minutes,
        "unique_counterparty_count":         unique_cp,
        "account_age_days":                  account_age_days,
        "is_new_high_volume_flag":           is_new_high_vol,
        "in_degree":                         in_degree,
        "out_degree":                        out_degree,
        "is_in_short_cycle":                 is_short_cycle,
        "betweenness_centrality":            betweenness,
        "fan_in_ratio":                      fan_in_ratio,
        "fan_out_ratio":                     fan_out_ratio,
        "amount_zscore_avg":                 amount_zscore,
        "round_number_txn_ratio":            round_num_ratio,
        "odd_hour_txn_ratio":                odd_hour_ratio,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    rng = np.random.default_rng(RANDOM_SEED)

    n_mule   = round(N_ROWS * MULE_RATE)
    n_benign = N_ROWS - n_mule

    print(f"Generating {N_ROWS} rows  ({n_mule} mule, {n_benign} benign) ...")

    # --- build feature dicts ---
    benign_feats = _generate_benign(rng, n_benign)
    mule_feats   = _generate_mule(rng, n_mule)

    # --- concatenate into a single dict ---
    combined: dict[str, list] = {}
    for col in SCHEMA_COLUMNS:
        if col == "account_id":
            ids = [f"ACC{str(i).zfill(6)}" for i in range(N_ROWS)]
            combined[col] = ids
        elif col == "is_mule_pattern":
            combined[col] = [0] * n_benign + [1] * n_mule
        else:
            combined[col] = list(benign_feats[col]) + list(mule_feats[col])

    df = pd.DataFrame(combined, columns=SCHEMA_COLUMNS)

    # Shuffle rows so mules are not all at the bottom
    df = df.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

    # ---------------------------------------------------------------------------
    # Inject realistic noise
    # ---------------------------------------------------------------------------
    # 1. Feature noise: add small Gaussian jitter to all continuous columns
    #    (sigma = 3% of each column's std) so the boundary is never razor-sharp
    continuous_cols = [
        c for c in SCHEMA_COLUMNS
        if c not in {"account_id", "is_mule_pattern", "is_new_high_volume_flag",
                     "is_in_short_cycle", "txn_count_1h", "txn_count_24h",
                     "txn_count_7d", "in_degree", "out_degree"}
    ]
    noise_rng = np.random.default_rng(RANDOM_SEED + 1)
    for col in continuous_cols:
        sigma = df[col].std() * 0.08   # 8% of std — meaningful but not signal-destroying
        df[col] = (df[col] + noise_rng.normal(0, sigma, size=len(df))).round(4)

    # 2. Label noise: flip ~15% of mule labels to 0 (missed detections)
    #    and ~2% of benign labels to 1 (false positives in the ground truth)
    #    This prevents the model from perfectly memorising the 50 mule rows.
    mule_idx   = df[df["is_mule_pattern"] == 1].index
    benign_idx = df[df["is_mule_pattern"] == 0].index

    flip_mule   = noise_rng.choice(mule_idx,   size=max(1, int(len(mule_idx)   * 0.15)), replace=False)
    flip_benign = noise_rng.choice(benign_idx,  size=max(1, int(len(benign_idx) * 0.02)), replace=False)

    df.loc[flip_mule,   "is_mule_pattern"] = 0
    df.loc[flip_benign, "is_mule_pattern"] = 1

    # ---------------------------------------------------------------------------
    # Schema integrity checks
    # ---------------------------------------------------------------------------
    assert list(df.columns) == SCHEMA_COLUMNS, "Column mismatch!"
    assert len(df) == N_ROWS, f"Row count mismatch: {len(df)}"
    assert df.isnull().sum().sum() == 0, "Unexpected nulls found!"
    float_cols = df.select_dtypes(include="float64").columns
    assert np.isfinite(df[float_cols].values).all(), "Non-finite float values found!"
    int_cols = [c for c in df.columns if df[c].dtype in (np.int64, np.int32)]
    assert (df[int_cols] >= 0).all().all(), "Negative int values found!"
    flag_cols = [c for c in df.columns if c.startswith("is_")]
    assert df[flag_cols].isin([0, 1]).all().all(), "Flag columns contain non-binary values!"

    # ---------------------------------------------------------------------------
    # Write CSV
    # ---------------------------------------------------------------------------
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"CSV written to: {OUTPUT_PATH}  ({len(df)} rows x {len(df.columns)} cols)\n")

    # ---------------------------------------------------------------------------
    # Acceptance criterion 1: label rate
    # ---------------------------------------------------------------------------
    actual_rate = df["is_mule_pattern"].mean()
    print(f"Label rate  ->  is_mule_pattern=1 : {actual_rate:.1%}  (target ~5 %)")
    assert 0.03 <= actual_rate <= 0.07, f"Mule rate {actual_rate:.2%} out of [3%,7%] band!"

    # ---------------------------------------------------------------------------
    # Acceptance criterion 2: correlation / mean-difference sanity check
    # ---------------------------------------------------------------------------
    mule_df   = df[df["is_mule_pattern"] == 1]
    benign_df = df[df["is_mule_pattern"] == 0]

    feature_cols = [c for c in SCHEMA_COLUMNS if c not in {"account_id", "is_mule_pattern"}]

    print("\n-- Mean comparison: mule (1) vs benign (0) --------------------------------")
    print(f"{'Feature':<40}  {'Mule mean':>12}  {'Benign mean':>12}  {'Ratio (M/B)':>12}")
    print("-" * 82)

    signal_features_found = 0
    SIGNAL_RATIO_THRESHOLD = 1.5   # mule mean must be >=1.5x or <=0.67x benign mean

    for col in feature_cols:
        m_mean = mule_df[col].mean()
        b_mean = benign_df[col].mean()
        ratio  = m_mean / (b_mean + EPS)
        flag   = ""
        if ratio >= SIGNAL_RATIO_THRESHOLD or ratio <= (1 / SIGNAL_RATIO_THRESHOLD):
            signal_features_found += 1
            flag = " <- signal"
        print(f"  {col:<38}  {m_mean:>12.4f}  {b_mean:>12.4f}  {ratio:>12.4f}{flag}")

    print("-" * 82)
    print(f"\nFeatures with clear signal (ratio >={SIGNAL_RATIO_THRESHOLD}x or <={1/SIGNAL_RATIO_THRESHOLD:.2f}x): "
          f"{signal_features_found}")

    if signal_features_found >= 3:
        print("PASSED: >=3 features show noticeably different means between mule and benign rows.")
    else:
        print("FAILED: Fewer than 3 features show clear signal -- review mock distributions.")
        sys.exit(1)


if __name__ == "__main__":
    main()
