"""
tests/test_features_temporal_change.py
========================================
Unit tests for temporal behavior-change feature module.
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import pandas as pd
import pytest

from app.services.features_temporal_change import (
    TEMPORAL_CHANGE_COLUMNS,
    compute_temporal_change_features,
    generate_behavioral_shift_visualization,
)


@pytest.fixture
def temporal_sample_txns() -> pd.DataFrame:
    """
    Create a controlled transaction DataFrame.
    Reference time: t_ref = 2026-01-05 12:00:00.
    Account 'ACC_SPIKE' has:
      - Historical baseline: 1 txn per day for 10 days (100.0 each)
      - Sudden burst in last 1h (11:00 to 12:00): 5 transactions of 5000.0 each!
    """
    t_ref = pd.Timestamp("2026-01-05 12:00:00")
    txns = []

    # 10 historical days
    for day in range(1, 11):
        txns.append({
            "timestamp": t_ref - pd.Timedelta(days=day),
            "sender_account_id": "ACC_SPIKE",
            "receiver_account_id": f"RECV_{day}",
            "amount": 100.0,
        })

    # Sudden burst in last 1 hour
    for min_offset in [5, 15, 25, 35, 45]:
        txns.append({
            "timestamp": t_ref - pd.Timedelta(minutes=min_offset),
            "sender_account_id": "ACC_SPIKE",
            "receiver_account_id": f"BURST_RECV_{min_offset}",
            "amount": 5000.0,
        })

    return pd.DataFrame(txns)


def test_current_vs_historical_ratios(temporal_sample_txns: pd.DataFrame):
    """Test 1h, 24h, and amount current-vs-historical ratios."""
    res = compute_temporal_change_features(temporal_sample_txns, as_of_timestamp="2026-01-05 12:00:00")
    spike_row = res[res["account_id"] == "ACC_SPIKE"].iloc[0]

    # Baseline hourly rate = 15 txns / 11 active hours = 1.36 txns/hour
    # Recent 1h count = 5 txns
    # Ratio > 1.0 (surge detected)
    assert spike_row["current_1h_vs_historical_ratio"] > 1.0
    assert spike_row["current_24h_vs_historical_ratio"] > 1.0
    assert spike_row["current_amount_vs_historical_ratio"] > 1.0


def test_frequency_and_amount_changes(temporal_sample_txns: pd.DataFrame):
    """Test transaction_frequency_change and average_amount_change."""
    res = compute_temporal_change_features(temporal_sample_txns, as_of_timestamp="2026-01-05 12:00:00")
    spike_row = res[res["account_id"] == "ACC_SPIKE"].iloc[0]

    assert spike_row["transaction_frequency_change"] > 0.0
    assert spike_row["average_amount_change"] > 1.0  # 5000.0 recent avg vs 1733.0 historical avg


def test_activity_and_velocity_spike_scores(temporal_sample_txns: pd.DataFrame):
    """Test activity_spike_score and velocity_change_score."""
    res = compute_temporal_change_features(temporal_sample_txns, as_of_timestamp="2026-01-05 12:00:00")
    spike_row = res[res["account_id"] == "ACC_SPIKE"].iloc[0]

    assert spike_row["activity_spike_score"] >= 1.0
    assert "velocity_change_score" in spike_row


def test_no_future_leakage(temporal_sample_txns: pd.DataFrame):
    """Verify that transactions occurring AFTER as_of_timestamp are strictly excluded."""
    # Set as_of_timestamp BEFORE the 1h burst (e.g. 10:00 AM)
    res_past = compute_temporal_change_features(temporal_sample_txns, as_of_timestamp="2026-01-05 10:00:00")
    past_row = res_past[res_past["account_id"] == "ACC_SPIKE"].iloc[0]

    # At 10:00 AM, the 11:15 to 11:55 burst hasn't happened yet!
    assert past_row["current_1h_vs_historical_ratio"] == 0.0


def test_visualization_generation(tmp_path):
    """Test generation of behavioral shift visualization chart."""
    chart_path = tmp_path / "test_shift.png"
    out = generate_behavioral_shift_visualization(chart_path)
    assert out.exists()
