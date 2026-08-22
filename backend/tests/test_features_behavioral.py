"""
tests/test_features_behavioral.py
===================================
Unit tests for the extended behavioral feature module.
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import pandas as pd
import pytest

from app.services.features_behavioral import (
    EXTENDED_BEHAVIORAL_COLUMNS,
    compute_behavioral_features,
    generate_behavioral_feature_dictionary,
)


@pytest.fixture
def sample_behavioral_txns() -> pd.DataFrame:
    """
    Create a controlled transaction DataFrame.
    Reference time: 2026-01-05 12:00:00 (Monday).
    'ACC_TARGET' has:
      - 2026-01-05 02:00:00 (Night, Monday): received 1000.0 from SENDER_1
      - 2026-01-05 03:00:00 (Night, Monday): sent 1000.0 to RECV_1
      - 2026-01-04 14:00:00 (Weekend, Sunday): received 500.0 from SENDER_2
      - 2026-01-04 15:00:00 (Weekend, Sunday): sent 500.0 to RECV_2
    """
    txns = [
        {"timestamp": "2026-01-05 02:00:00", "sender_account_id": "SENDER_1", "receiver_account_id": "ACC_TARGET", "amount": 1000.0},
        {"timestamp": "2026-01-05 03:00:00", "sender_account_id": "ACC_TARGET", "receiver_account_id": "RECV_1", "amount": 1000.0},
        {"timestamp": "2026-01-04 14:00:00", "sender_account_id": "SENDER_2", "receiver_account_id": "ACC_TARGET", "amount": 500.0},
        {"timestamp": "2026-01-04 15:00:00", "sender_account_id": "ACC_TARGET", "receiver_account_id": "RECV_2", "amount": 500.0},
    ]
    return pd.DataFrame(txns)


def test_counterparty_diversity(sample_behavioral_txns: pd.DataFrame):
    """Test unique_sender_count, unique_receiver_count, and unique_counterparty_count."""
    res = compute_behavioral_features(sample_behavioral_txns, as_of_timestamp="2026-01-05 12:00:00")
    target = res[res["account_id"] == "ACC_TARGET"].iloc[0]

    assert target["unique_sender_count"] == 2  # SENDER_1, SENDER_2
    assert target["unique_receiver_count"] == 2  # RECV_1, RECV_2
    assert target["unique_counterparty_count"] == 4


def test_transaction_ratios(sample_behavioral_txns: pd.DataFrame):
    """Test incoming_transaction_ratio and outgoing_transaction_ratio."""
    res = compute_behavioral_features(sample_behavioral_txns, as_of_timestamp="2026-01-05 12:00:00")
    target = res[res["account_id"] == "ACC_TARGET"].iloc[0]

    # 2 incoming, 2 outgoing -> total = 4
    assert pytest.approx(target["incoming_transaction_ratio"], 0.01) == 0.50
    assert pytest.approx(target["outgoing_transaction_ratio"], 0.01) == 0.50


def test_temporal_and_offpeak_patterns(sample_behavioral_txns: pd.DataFrame):
    """Test active_days, active_hours, night_transaction_ratio, weekend_transaction_ratio."""
    res = compute_behavioral_features(sample_behavioral_txns, as_of_timestamp="2026-01-05 12:00:00")
    target = res[res["account_id"] == "ACC_TARGET"].iloc[0]

    assert target["active_days"] == 2  # Jan 4 and Jan 5
    assert target["active_hours"] == 4  # Hours 2, 3, 14, 15

    # Night txns: 02:00 and 03:00 -> 2 out of 4 = 50%
    assert pytest.approx(target["night_transaction_ratio"], 0.01) == 0.50

    # Weekend txns: Jan 4 (Sunday) -> 2 out of 4 = 50%
    assert pytest.approx(target["weekend_transaction_ratio"], 0.01) == 0.50


def test_monetary_dispersion(sample_behavioral_txns: pd.DataFrame):
    """Test transaction_amount_std and transaction_amount_cv."""
    res = compute_behavioral_features(sample_behavioral_txns, as_of_timestamp="2026-01-05 12:00:00")
    target = res[res["account_id"] == "ACC_TARGET"].iloc[0]

    # Amounts: 1000, 1000, 500, 500
    # Mean = 750, Std ≈ 288.67
    assert target["transaction_amount_std"] > 0.0
    assert target["transaction_amount_cv"] > 0.0


def test_new_account_high_volume_flag():
    """Test new_account_high_volume_flag."""
    t0 = pd.Timestamp("2026-01-05 12:00:00")
    # Account NEW_HV created 5 days ago with 12 transactions in 7d
    txns = [
        {"timestamp": t0 - pd.Timedelta(hours=i), "sender_account_id": "NEW_HV", "receiver_account_id": "OTHER", "amount": 100.0}
        for i in range(12)
    ]
    df = pd.DataFrame(txns)
    res = compute_behavioral_features(df, as_of_timestamp="2026-01-05 12:00:00")
    target = res[res["account_id"] == "NEW_HV"].iloc[0]

    assert target["account_age_days"] <= 5
    assert target["new_account_high_volume_flag"] == 1


def test_feature_dictionary_generation():
    """Verify feature dictionary completeness."""
    fdict = generate_behavioral_feature_dictionary()
    assert len(fdict) >= 15
    assert "unique_sender_count" in fdict
    assert "night_transaction_ratio" in fdict
    assert "formula" in fdict["night_transaction_ratio"]
    assert "mule_signal" in fdict["night_transaction_ratio"]
