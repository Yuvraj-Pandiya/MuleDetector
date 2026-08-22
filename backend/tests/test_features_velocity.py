"""
tests/test_features_velocity.py
=================================
Unit tests for extended velocity feature module.
"""

from __future__ import annotations

import sys
from pathlib import Path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import pandas as pd
import pytest

from app.services.features_velocity import (
    EXTENDED_VELOCITY_COLUMNS,
    VELOCITY_COLUMNS,
    compute_velocity_features,
)


@pytest.fixture
def sample_transactions() -> pd.DataFrame:
    """
    Create a controlled transaction DataFrame relative to reference time t_ref = 2026-01-02 12:00:00.
    Account 'ACC_A' has:
      - 2m ago (11:58): sent 100.0 (out)
      - 10m ago (11:50): received 500.0 (in)
      - 45m ago (11:15): sent 200.0 (out)
      - 3h ago (09:00): received 1000.0 (in)
      - 12h ago (00:00): sent 400.0 (out)
      - 3 days ago: received 2000.0 (in)
      - 10 days ago (OUTSIDE 7d window): sent 5000.0 (out)
    """
    t_ref = pd.Timestamp("2026-01-02 12:00:00")
    txns = [
        # 10 days ago (2025-12-23)
        {"timestamp": t_ref - pd.Timedelta(days=10), "sender_account_id": "ACC_A", "receiver_account_id": "ACC_B", "amount": 5000.0},
        # 3 days ago (2025-12-30)
        {"timestamp": t_ref - pd.Timedelta(days=3),  "sender_account_id": "ACC_B", "receiver_account_id": "ACC_A", "amount": 2000.0},
        # 12 hours ago
        {"timestamp": t_ref - pd.Timedelta(hours=12), "sender_account_id": "ACC_A", "receiver_account_id": "ACC_C", "amount": 400.0},
        # 3 hours ago
        {"timestamp": t_ref - pd.Timedelta(hours=3),  "sender_account_id": "ACC_C", "receiver_account_id": "ACC_A", "amount": 1000.0},
        # 45 mins ago
        {"timestamp": t_ref - pd.Timedelta(minutes=45), "sender_account_id": "ACC_A", "receiver_account_id": "ACC_B", "amount": 200.0},
        # 10 mins ago
        {"timestamp": t_ref - pd.Timedelta(minutes=10), "sender_account_id": "ACC_B", "receiver_account_id": "ACC_A", "amount": 500.0},
        # 2 mins ago
        {"timestamp": t_ref - pd.Timedelta(minutes=2),  "sender_account_id": "ACC_A", "receiver_account_id": "ACC_C", "amount": 100.0},
    ]
    return pd.DataFrame(txns)


def test_time_window_counts(sample_transactions: pd.DataFrame):
    """Test 5m, 15m, 1h, 6h, 24h, 7d transaction count calculations."""
    res = compute_velocity_features(sample_transactions, as_of_timestamp="2026-01-02 12:00:00")
    row_a = res[res["account_id"] == "ACC_A"].iloc[0]

    # ACC_A txns within t_ref (2026-01-02 12:00:00):
    # 5m (>=11:55): 1 (2m ago)
    assert row_a["txn_count_5min"] == 1

    # 15m (>=11:45): 2 (2m ago, 10m ago)
    assert row_a["txn_count_15min"] == 2

    # 1h (>=11:00): 3 (2m ago, 10m ago, 45m ago)
    assert row_a["txn_count_1h"] == 3

    # 6h (>=06:00): 4 (2m, 10m, 45m, 3h ago)
    assert row_a["txn_count_6h"] == 4

    # 24h (>=yesterday 12:00): 5 (2m, 10m, 45m, 3h, 12h ago)
    assert row_a["txn_count_24h"] == 5

    # 7d (>=7 days ago): 6 (all except 10d ago)
    assert row_a["txn_count_7d"] == 6


def test_directional_amounts(sample_transactions: pd.DataFrame):
    """Test 1h, 24h, 7d inbound and outbound amount sums."""
    res = compute_velocity_features(sample_transactions, as_of_timestamp="2026-01-02 12:00:00")
    row_a = res[res["account_id"] == "ACC_A"].iloc[0]

    # Within 1h:
    # out: 100.0 (2m) + 200.0 (45m) = 300.0
    # in: 500.0 (10m) = 500.0
    assert pytest.approx(row_a["amount_out_1h"], 0.01) == 300.0
    assert pytest.approx(row_a["amount_in_1h"], 0.01) == 500.0

    # Within 24h:
    # out: 300.0 (1h) + 400.0 (12h) = 700.0
    # in: 500.0 (1h) + 1000.0 (3h) = 1500.0
    assert pytest.approx(row_a["amount_out_24h"], 0.01) == 700.0
    assert pytest.approx(row_a["amount_in_24h"], 0.01) == 1500.0
    assert pytest.approx(row_a["total_amount_out_24h"], 0.01) == 700.0
    assert pytest.approx(row_a["total_amount_in_24h"], 0.01) == 1500.0

    # Within 7d:
    # in: 1500.0 (24h) + 2000.0 (3d) = 3500.0
    assert pytest.approx(row_a["amount_in_7d"], 0.01) == 3500.0


def test_amount_aggregations(sample_transactions: pd.DataFrame):
    """Test max, average, and median transaction amount metrics."""
    res = compute_velocity_features(sample_transactions, as_of_timestamp="2026-01-02 12:00:00")
    row_a = res[res["account_id"] == "ACC_A"].iloc[0]

    # ACC_A txns up to t_ref: 100, 500, 200, 1000, 400, 2000, 5000
    amounts = [100.0, 500.0, 200.0, 1000.0, 400.0, 2000.0, 5000.0]
    assert pytest.approx(row_a["max_transaction_amount"], 0.01) == max(amounts)
    assert pytest.approx(row_a["average_transaction_amount"], 0.01) == (sum(amounts) / len(amounts))
    assert pytest.approx(row_a["median_transaction_amount"], 0.01) == 500.0


def test_velocity_change_indicators(sample_transactions: pd.DataFrame):
    """Test transaction_velocity_change and recent_volume_vs_historical_volume ratios."""
    res = compute_velocity_features(sample_transactions, as_of_timestamp="2026-01-02 12:00:00")
    row_a = res[res["account_id"] == "ACC_A"].iloc[0]

    # txn_count_1h = 3, txn_count_24h = 5
    # baseline_hourly = 5 / 24 = 0.20833
    # velocity_change = 3 / 0.20833 ≈ 14.40
    assert row_a["transaction_velocity_change"] > 1.0

    # amount_in_1h + amount_out_1h = 800.0
    # amount_in_24h + amount_out_24h = 2200.0 -> hourly avg = 2200/24 = 91.666
    # volume_ratio = 800 / 91.666 ≈ 8.72
    assert row_a["recent_volume_vs_historical_volume"] > 1.0


def test_no_future_leakage(sample_transactions: pd.DataFrame):
    """Verify that specifying as_of_timestamp strictly excludes future transactions."""
    # Set as_of_timestamp BEFORE 2m and 10m transactions (e.g. 11:30)
    res_past = compute_velocity_features(sample_transactions, as_of_timestamp="2026-01-02 11:30:00")
    row_a_past = res_past[res_past["account_id"] == "ACC_A"].iloc[0]

    # At 11:30, the 11:58 (2m ago) and 11:50 (10m ago) txns haven't happened yet!
    # max_transaction_amount up to 11:30 should NOT see 100.0 or 500.0 from 11:58/11:50
    assert row_a_past["txn_count_5min"] == 0
    assert row_a_past["amount_out_1h"] == 200.0  # only 11:15 txn
