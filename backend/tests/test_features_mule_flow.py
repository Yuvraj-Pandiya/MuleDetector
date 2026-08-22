"""
tests/test_features_mule_flow.py
==================================
Unit tests for the mule fund-flow feature module.
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import pandas as pd
import pytest

from app.services.features_mule_flow import (
    MULE_FLOW_COLUMNS,
    compute_mule_flow_features,
)


def test_immediate_pass_through():
    """Test account receiving funds and immediately forwarding them within 2 minutes."""
    t0 = pd.Timestamp("2026-01-01 10:00:00")
    txns = pd.DataFrame([
        # Inbound to MULE_1 at 10:00
        {"timestamp": t0, "sender_account_id": "CLEAN_1", "receiver_account_id": "MULE_1", "amount": 1000.0},
        # Outbound from MULE_1 at 10:02 (2 minutes later)
        {"timestamp": t0 + pd.Timedelta(minutes=2), "sender_account_id": "MULE_1", "receiver_account_id": "CLEAN_2", "amount": 950.0},
    ])

    res = compute_mule_flow_features(txns)
    mule = res[res["account_id"] == "MULE_1"].iloc[0]

    assert mule["avg_time_to_forward_funds"] == 2.0
    assert mule["min_time_to_forward_funds"] == 2.0
    assert mule["pct_funds_forwarded_within_5min"] == 1.0
    assert mule["pct_funds_forwarded_within_15min"] == 1.0
    assert mule["pct_funds_forwarded_within_1hour"] == 1.0
    assert mule["same_day_fund_forwarding_ratio"] == 1.0


def test_delayed_pass_through():
    """Test account receiving funds and forwarding them 8 hours later."""
    t0 = pd.Timestamp("2026-01-01 10:00:00")
    txns = pd.DataFrame([
        {"timestamp": t0, "sender_account_id": "SRC", "receiver_account_id": "DELAYED_MULE", "amount": 5000.0},
        # Outbound 8 hours (480 minutes) later
        {"timestamp": t0 + pd.Timedelta(hours=8), "sender_account_id": "DELAYED_MULE", "receiver_account_id": "DEST", "amount": 5000.0},
    ])

    res = compute_mule_flow_features(txns)
    row = res[res["account_id"] == "DELAYED_MULE"].iloc[0]

    assert row["avg_time_to_forward_funds"] == 480.0
    assert row["pct_funds_forwarded_within_5min"] == 0.0
    assert row["pct_funds_forwarded_within_15min"] == 0.0
    assert row["pct_funds_forwarded_within_1hour"] == 0.0
    assert row["same_day_fund_forwarding_ratio"] == 1.0  # within 24h/same day


def test_no_outgoing_activity():
    """Test account receiving funds with NO subsequent outgoing transactions."""
    t0 = pd.Timestamp("2026-01-01 10:00:00")
    txns = pd.DataFrame([
        {"timestamp": t0, "sender_account_id": "SRC", "receiver_account_id": "SAVER_1", "amount": 10000.0},
    ])

    res = compute_mule_flow_features(txns)
    saver = res[res["account_id"] == "SAVER_1"].iloc[0]

    # Safe defaults for accounts with no outgoing activity
    assert saver["avg_time_to_forward_funds"] == 1440.0
    assert saver["pct_funds_forwarded_within_5min"] == 0.0
    assert saver["pct_funds_forwarded_within_1hour"] == 0.0
    assert saver["fund_retention_ratio"] == 1.0  # Retained 100% of inflow


def test_multiple_incoming_transactions():
    """Test matching multiple incoming transactions to subsequent outgoing transactions."""
    t0 = pd.Timestamp("2026-01-01 10:00:00")
    txns = pd.DataFrame([
        # Inbound 1 at 10:00 (1000.0)
        {"timestamp": t0, "sender_account_id": "SRC_1", "receiver_account_id": "MULTI_IN", "amount": 1000.0},
        # Inbound 2 at 11:00 (2000.0)
        {"timestamp": t0 + pd.Timedelta(hours=1), "sender_account_id": "SRC_2", "receiver_account_id": "MULTI_IN", "amount": 2000.0},
        # Outbound at 11:10 (2000.0)
        {"timestamp": t0 + pd.Timedelta(hours=1, minutes=10), "sender_account_id": "MULTI_IN", "receiver_account_id": "DEST_1", "amount": 3000.0},
    ])

    res = compute_mule_flow_features(txns)
    acc = res[res["account_id"] == "MULTI_IN"].iloc[0]

    # Inbound 1 (10:00) -> Outbound at 11:10 (delay = 70 min)
    # Inbound 2 (11:00) -> Outbound at 11:10 (delay = 10 min)
    # Average delay = (70 + 10) / 2 = 40 min
    # Min delay = 10 min
    assert acc["avg_time_to_forward_funds"] == 40.0
    assert acc["min_time_to_forward_funds"] == 10.0
    assert acc["pct_funds_forwarded_within_15min"] > 0.0  # Inbound 2 was within 15m


def test_multiple_outgoing_transactions():
    """Test matching when there are multiple outgoing transactions in sequence."""
    t0 = pd.Timestamp("2026-01-01 10:00:00")
    txns = pd.DataFrame([
        # Inbound at 10:00 (5000.0)
        {"timestamp": t0, "sender_account_id": "SRC_1", "receiver_account_id": "MULTI_OUT", "amount": 5000.0},
        # Outbound 1 at 10:04 (2000.0) -> First subsequent outgoing matches Inbound 1
        {"timestamp": t0 + pd.Timedelta(minutes=4), "sender_account_id": "MULTI_OUT", "receiver_account_id": "DEST_1", "amount": 2000.0},
        # Outbound 2 at 10:30 (3000.0)
        {"timestamp": t0 + pd.Timedelta(minutes=30), "sender_account_id": "MULTI_OUT", "receiver_account_id": "DEST_2", "amount": 3000.0},
    ])

    res = compute_mule_flow_features(txns)
    acc = res[res["account_id"] == "MULTI_OUT"].iloc[0]

    # Inbound 1 (10:00) matched to first subsequent outgoing (10:04) -> delay = 4 min <= 5m
    assert acc["min_time_to_forward_funds"] == 4.0
    assert acc["pct_funds_forwarded_within_5min"] == 1.0
    assert pytest.approx(acc["outgoing_to_incoming_amount_ratio"], 0.01) == 1.0
