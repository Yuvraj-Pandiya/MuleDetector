"""
app/services/mock_generator.py
================================
Self-contained mock feature generator for MuleDetector backend fallback.
Generates synthetic feature matrix CSV at app/data/mock_features.csv.
"""

from __future__ import annotations

import pathlib
import numpy as np
import pandas as pd

_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
OUTPUT_PATH = _DATA_DIR / "mock_features.csv"
N_ROWS = 1000
MULE_RATE = 0.05
RANDOM_SEED = 42
EPS = 1e-6

SCHEMA_COLUMNS = [
    "account_id",
    "txn_count_1h", "txn_count_24h", "txn_count_7d",
    "total_amount_out_24h", "total_amount_in_24h",
    "avg_transaction_amount", "max_transaction_amount",
    "ratio_received_to_sent_24h", "avg_time_to_forward_funds_minutes",
    "unique_counterparty_count", "account_age_days", "is_new_high_volume_flag",
    "in_degree", "out_degree", "is_in_short_cycle",
    "betweenness_centrality", "fan_in_ratio", "fan_out_ratio",
    "amount_zscore_avg", "round_number_txn_ratio", "odd_hour_txn_ratio",
    "is_mule_pattern",
]


def generate_mock_features_csv(output_path: pathlib.Path = OUTPUT_PATH) -> pd.DataFrame:
    """Generate a 1000-row synthetic feature DataFrame and save to CSV."""
    rng = np.random.default_rng(RANDOM_SEED)
    n_mule = round(N_ROWS * MULE_RATE)
    n_benign = N_ROWS - n_mule

    # Benign
    b_txn_1h = rng.integers(0, 8, size=n_benign)
    b_txn_24h = rng.integers(1, 50, size=n_benign)
    b_txn_7d = rng.integers(5, 200, size=n_benign)
    b_amt_out = rng.uniform(50, 8000, size=n_benign).round(2)
    b_amt_in = rng.uniform(50, 8000, size=n_benign).round(2)
    b_avg_amt = rng.uniform(20, 800, size=n_benign).round(2)
    b_max_amt = (b_avg_amt + rng.uniform(0, 800, size=n_benign)).round(2)
    b_ratio = (b_amt_in / (b_amt_out + EPS)).round(4)
    b_fwd = rng.uniform(30, 1440, size=n_benign).round(2)
    b_cp = rng.integers(1, 40, size=n_benign)
    b_age = rng.integers(20, 3650, size=n_benign)
    b_flag = ((b_age < 30) & (b_txn_7d > 50)).astype(int)
    b_in_deg = rng.integers(1, 25, size=n_benign)
    b_out_deg = rng.integers(1, 35, size=n_benign)
    b_tot_deg = b_in_deg + b_out_deg + EPS
    b_cycle = rng.choice([0, 1], size=n_benign, p=[0.88, 0.12])
    b_betw = rng.uniform(0.0, 0.15, size=n_benign).round(6)
    b_fan_in = (b_in_deg / b_tot_deg).round(4)
    b_fan_out = (b_out_deg / b_tot_deg).round(4)
    b_zscore = rng.normal(0.3, 1.0, size=n_benign).round(4)
    b_round = rng.uniform(0.05, 0.50, size=n_benign).round(4)
    b_odd = rng.uniform(0.02, 0.45, size=n_benign).round(4)

    # Mule
    m_txn_1h = rng.integers(2, 15, size=n_mule)
    m_txn_24h = rng.integers(10, 80, size=n_mule)
    m_txn_7d = rng.integers(30, 350, size=n_mule)
    m_amt_out = rng.uniform(200, 15000, size=n_mule).round(2)
    m_amt_in = (m_amt_out * rng.uniform(1.1, 2.5, size=n_mule)).round(2)
    m_avg_amt = rng.uniform(100, 2000, size=n_mule).round(2)
    m_max_amt = (m_avg_amt + rng.uniform(200, 4000, size=n_mule)).round(2)
    m_ratio = (m_amt_in / (m_amt_out + EPS)).round(4)
    m_fwd = rng.uniform(5, 300, size=n_mule).round(2)
    m_cp = rng.integers(3, 50, size=n_mule)
    m_age = rng.integers(5, 365, size=n_mule)
    m_flag = ((m_age < 30) & (m_txn_7d > 50)).astype(int)
    m_in_deg = rng.integers(2, 20, size=n_mule)
    m_out_deg = rng.integers(10, 50, size=n_mule)
    m_tot_deg = m_in_deg + m_out_deg + EPS
    m_cycle = rng.choice([0, 1], size=n_mule, p=[0.55, 0.45])
    m_betw = rng.uniform(0.02, 0.25, size=n_mule).round(6)
    m_fan_in = (m_in_deg / m_tot_deg).round(4)
    m_fan_out = (m_out_deg / m_tot_deg).round(4)
    m_zscore = rng.normal(1.5, 1.0, size=n_mule).round(4)
    m_round = rng.uniform(0.25, 0.80, size=n_mule).round(4)
    m_odd = rng.uniform(0.20, 0.75, size=n_mule).round(4)

    combined = {
        "account_id": [f"ACC{str(i).zfill(6)}" for i in range(N_ROWS)],
        "txn_count_1h": list(b_txn_1h) + list(m_txn_1h),
        "txn_count_24h": list(b_txn_24h) + list(m_txn_24h),
        "txn_count_7d": list(b_txn_7d) + list(m_txn_7d),
        "total_amount_out_24h": list(b_amt_out) + list(m_amt_out),
        "total_amount_in_24h": list(b_amt_in) + list(m_amt_in),
        "avg_transaction_amount": list(b_avg_amt) + list(m_avg_amt),
        "max_transaction_amount": list(b_max_amt) + list(m_max_amt),
        "ratio_received_to_sent_24h": list(b_ratio) + list(m_ratio),
        "avg_time_to_forward_funds_minutes": list(b_fwd) + list(m_fwd),
        "unique_counterparty_count": list(b_cp) + list(m_cp),
        "account_age_days": list(b_age) + list(m_age),
        "is_new_high_volume_flag": list(b_flag) + list(m_flag),
        "in_degree": list(b_in_deg) + list(m_in_deg),
        "out_degree": list(b_out_deg) + list(m_out_deg),
        "is_in_short_cycle": list(b_cycle) + list(m_cycle),
        "betweenness_centrality": list(b_betw) + list(m_betw),
        "fan_in_ratio": list(b_fan_in) + list(m_fan_in),
        "fan_out_ratio": list(b_fan_out) + list(m_fan_out),
        "amount_zscore_avg": list(b_zscore) + list(m_zscore),
        "round_number_txn_ratio": list(b_round) + list(m_round),
        "odd_hour_txn_ratio": list(b_odd) + list(m_odd),
        "is_mule_pattern": [0] * n_benign + [1] * n_mule,
    }

    df = pd.DataFrame(combined, columns=SCHEMA_COLUMNS)
    df = df.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

    # Feature jitter
    cont_cols = ["amount_zscore_avg", "betweenness_centrality", "ratio_received_to_sent_24h"]
    noise_rng = np.random.default_rng(RANDOM_SEED + 1)
    for col in cont_cols:
        sigma = df[col].std() * 0.08
        df[col] = (df[col] + noise_rng.normal(0, sigma, size=len(df))).round(4)

    # Label noise
    mule_idx = df[df["is_mule_pattern"] == 1].index
    benign_idx = df[df["is_mule_pattern"] == 0].index
    flip_mule = noise_rng.choice(mule_idx, size=max(1, int(len(mule_idx) * 0.15)), replace=False)
    flip_benign = noise_rng.choice(benign_idx, size=max(1, int(len(benign_idx) * 0.02)), replace=False)
    df.loc[flip_mule, "is_mule_pattern"] = 0
    df.loc[flip_benign, "is_mule_pattern"] = 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return df
