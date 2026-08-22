"""
tests/test_alert_generator.py
==============================
Unit test suite for prioritized risk-based alert engine and deduplication window.
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import pandas as pd
import pytest

from app.services.alert_generator import (
    VALID_STATUSES,
    generate_alerts,
    get_alerts,
    update_alert_status,
)


@pytest.fixture
def sample_scored_df():
    """Generate synthetic scored DataFrame for alert generator tests."""
    return pd.DataFrame([
        {
            "account_id": "ACC_ALPHA",
            "risk_score": 92.5,
            "risk_tier": "CRITICAL",
            "anomaly_score": 0.88,
            "network_risk_score": 91.0,
            "unique_counterparties": 15,
            "top_reasons": ["unusually high outgoing velocity", "rapid fund forwarding"],
            "top_features": ["txn_count_1h", "avg_time_to_forward_funds_minutes"],
        },
        {
            "account_id": "ACC_BETA",
            "risk_score": 76.0,
            "risk_tier": "HIGH",
            "anomaly_score": 0.65,
            "network_risk_score": 72.0,
            "unique_counterparties": 8,
            "top_reasons": ["large number of counterparties", "high network centrality"],
            "top_features": ["unique_counterparty_count", "betweenness_centrality"],
        },
        {
            "account_id": "ACC_GAMMA",
            "risk_score": 15.0,
            "risk_tier": "LOW",
            "anomaly_score": 0.10,
            "network_risk_score": 12.0,
            "unique_counterparties": 2,
            "top_reasons": ["low short-term transaction velocity"],
            "top_features": ["txn_count_1h"],
        },
    ])


def test_generate_prioritized_alerts_schema(sample_scored_df):
    alerts = generate_alerts(sample_scored_df, threshold=30.0)

    assert len(alerts) == 2
    required_fields = {
        "alert_id", "account_id", "risk_score", "risk_tier", "top_reasons",
        "anomaly_score", "network_risk", "model_version", "created_at", "status"
    }

    for alert in alerts:
        assert required_fields.issubset(set(alert.keys()))
        assert alert["status"] == "OPEN"
        assert alert["risk_score"] >= 30.0


def test_supported_status_transitions(sample_scored_df):
    alerts = generate_alerts(sample_scored_df, threshold=30.0)
    alert_id = alerts[0]["alert_id"]

    for new_st in ["UNDER_INVESTIGATION", "CONFIRMED_MULE", "FALSE_POSITIVE", "DISMISSED", "OPEN"]:
        updated = update_alert_status(alert_id, new_st)
        assert updated["status"] == new_st


def test_invalid_status_rejection():
    with pytest.raises(ValueError):
        update_alert_status("ALT-NONEXISTENT", "INVALID_STATUS")


def test_alert_deduplication_window(sample_scored_df):
    alerts_1 = generate_alerts(sample_scored_df, threshold=30.0, dedup_window_hours=24.0)
    count_1 = len(alerts_1)
    alert_id_alpha = alerts_1[0]["alert_id"]

    # Re-run generate_alerts immediately with slightly updated score for same accounts
    sample_scored_df.loc[sample_scored_df["account_id"] == "ACC_ALPHA", "risk_score"] = 95.0
    alerts_2 = generate_alerts(sample_scored_df, threshold=30.0, dedup_window_hours=24.0)

    # Should update existing alert rather than inserting duplicate alert rows
    alpha_alert = [a for a in alerts_2 if a["account_id"] == "ACC_ALPHA"][0]
    assert alpha_alert["alert_id"] == alert_id_alpha
    assert alpha_alert["risk_score"] == 95.0


def test_analyst_queue_sorting(sample_scored_df):
    generate_alerts(sample_scored_df, threshold=30.0)
    prioritized = get_alerts(sort_by="prioritized")

    assert len(prioritized) >= 2
    # Verify sorting order: risk_score DESC
    assert prioritized[0]["risk_score"] >= prioritized[1]["risk_score"]
