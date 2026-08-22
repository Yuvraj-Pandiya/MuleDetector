"""
tests/test_risk_scorer.py
==========================
Unit test suite for CalibratedRiskScorer and score_accounts.
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import numpy as np
import pandas as pd
import pytest

from app.services.risk_scorer import CalibratedRiskScorer, score_accounts


@pytest.fixture
def sample_feature_df():
    """Generate synthetic DataFrame for account risk scoring."""
    np.random.seed(42)
    n = 100
    is_mule = np.zeros(n, dtype=int)
    is_mule[:15] = 1

    return pd.DataFrame({
        "account_id": [f"ACC_{i:04d}" for i in range(n)],
        "txn_count_1h": np.random.randint(0, 10, n),
        "txn_count_24h": np.random.randint(1, 50, n),
        "txn_count_7d": np.random.randint(5, 200, n),
        "total_amount_out_24h": np.random.uniform(50, 5000, n),
        "total_amount_in_24h": np.random.uniform(50, 5000, n),
        "avg_transaction_amount": np.random.uniform(10, 500, n),
        "max_transaction_amount": np.random.uniform(50, 1000, n),
        "ratio_received_to_sent_24h": np.random.uniform(0.1, 2.0, n),
        "avg_time_to_forward_funds_minutes": np.random.uniform(5, 500, n),
        "unique_counterparty_count": np.random.randint(1, 20, n),
        "account_age_days": np.random.randint(1, 365, n),
        "is_new_high_volume_flag": np.random.choice([0, 1], n),
        "in_degree": np.random.randint(1, 10, n),
        "out_degree": np.random.randint(1, 10, n),
        "is_in_short_cycle": np.random.choice([0, 1], n),
        "betweenness_centrality": np.random.uniform(0, 0.1, n),
        "fan_in_ratio": np.random.uniform(0, 1, n),
        "fan_out_ratio": np.random.uniform(0, 1, n),
        "amount_zscore_avg": np.random.uniform(-1, 3, n),
        "round_number_txn_ratio": np.random.uniform(0, 1, n),
        "odd_hour_txn_ratio": np.random.uniform(0, 1, n),
        "is_mule_pattern": is_mule,
    })


def test_calibrated_risk_score_bounds():
    scorer = CalibratedRiskScorer()
    
    # Test lower bound
    s_min = scorer.calculate_risk_score(0.0, 0.0, 0.0)
    assert s_min == 0.0

    # Test upper bound
    s_max = scorer.calculate_risk_score(1.0, 1.0, 100.0)
    assert s_max == 100.0

    # Vectorized test
    p_sup = np.array([0.1, 0.5, 0.9])
    s_anom = np.array([0.2, 0.4, 0.8])
    s_net = np.array([10.0, 50.0, 90.0])
    scores = scorer.calculate_risk_score(p_sup, s_anom, s_net)

    assert len(scores) == 3
    assert all(0.0 <= s <= 100.0 for s in scores)
    assert scores[0] < scores[1] < scores[2]


def test_configurable_risk_tiers():
    custom_tiers = {
        "Low": (0.0, 20.0),
        "Medium": (20.0, 60.0),
        "High": (60.0, 80.0),
        "Critical": (80.0, 100.0),
    }

    scorer = CalibratedRiskScorer(risk_tier_config=custom_tiers)

    assert scorer.assign_risk_tier(10.0) == "Low"
    assert scorer.assign_risk_tier(40.0) == "Medium"
    assert scorer.assign_risk_tier(75.0) == "High"
    assert scorer.assign_risk_tier(90.0) == "Critical"


def test_candidate_threshold_evaluation(sample_feature_df):
    scorer = CalibratedRiskScorer()
    y_true = sample_feature_df["is_mule_pattern"].values
    risk_scores = np.random.uniform(0, 100, size=len(y_true))

    eval_table = scorer.evaluate_candidate_thresholds(
        y_true=y_true,
        risk_scores=risk_scores,
        candidate_thresholds=[20.0, 50.0, 80.0],
    )

    assert len(eval_table) == 3
    for row in eval_table:
        assert "threshold" in row
        assert "precision" in row
        assert "recall" in row
        assert "f1_score" in row
        assert "alert_volume_count" in row
        assert "alert_volume_pct" in row
        assert "false_positive_rate" in row
        assert 0.0 <= row["precision"] <= 1.0
        assert 0.0 <= row["recall"] <= 1.0
        assert 0.0 <= row["false_positive_rate"] <= 1.0


def test_score_accounts_integration(sample_feature_df):
    results = score_accounts(sample_feature_df)

    assert isinstance(results, pd.DataFrame)
    assert len(results) == len(sample_feature_df)
    
    expected_cols = {
        "account_id", "risk_score", "risk_tier", "mule_probability",
        "anomaly_score", "network_risk_score", "top_features"
    }
    assert expected_cols.issubset(set(results.columns))

    assert all(0.0 <= s <= 100.0 for s in results["risk_score"])
    assert set(results["risk_tier"].unique()).issubset({"Low", "Medium", "High", "Critical"})
