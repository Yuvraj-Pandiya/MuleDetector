"""
tests/test_explainer.py
========================
Unit test suite for upgraded SHAP explainer module.
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import numpy as np
import pandas as pd
import pytest

from app.services.explainer import explain_account, explain_flagged_accounts


@pytest.fixture
def sample_feature_df():
    """Generate synthetic DataFrame for SHAP explanation tests."""
    np.random.seed(42)
    n = 20
    is_mule = np.zeros(n, dtype=int)
    is_mule[:5] = 1

    return pd.DataFrame({
        "account_id": [f"ACC_{i:04d}" for i in range(n)],
        "txn_count_1h": np.random.randint(0, 10, n) + is_mule * 15,
        "txn_count_24h": np.random.randint(1, 50, n) + is_mule * 100,
        "txn_count_7d": np.random.randint(5, 200, n),
        "total_amount_out_24h": np.random.uniform(50, 5000, n) + is_mule * 50000,
        "total_amount_in_24h": np.random.uniform(50, 5000, n) + is_mule * 52000,
        "avg_transaction_amount": np.random.uniform(10, 500, n) + is_mule * 2000,
        "max_transaction_amount": np.random.uniform(50, 1000, n),
        "ratio_received_to_sent_24h": np.random.uniform(0.1, 2.0, n),
        "avg_time_to_forward_funds_minutes": np.random.uniform(5, 500, n),
        "unique_counterparty_count": np.random.randint(1, 20, n) + is_mule * 15,
        "account_age_days": np.random.randint(1, 365, n),
        "is_new_high_volume_flag": is_mule,
        "in_degree": np.random.randint(1, 10, n),
        "out_degree": np.random.randint(1, 10, n) + is_mule * 10,
        "is_in_short_cycle": is_mule,
        "betweenness_centrality": np.random.uniform(0, 0.1, n) + is_mule * 0.4,
        "fan_in_ratio": np.random.uniform(0, 1, n),
        "fan_out_ratio": np.random.uniform(0, 1, n) + is_mule * 3.0,
        "amount_zscore_avg": np.random.uniform(-1, 3, n) + is_mule * 4.0,
        "round_number_txn_ratio": np.random.uniform(0, 1, n),
        "odd_hour_txn_ratio": np.random.uniform(0, 1, n),
        "is_mule_pattern": is_mule,
    })


def test_explain_account_shap_outputs(sample_feature_df):
    acct_id = "ACC_0000"
    exp = explain_account(acct_id, sample_feature_df)

    assert exp["account_id"] == acct_id
    assert "risk_score" in exp
    assert "risk_tier" in exp
    assert "top_positive_features" in exp
    assert "top_negative_features" in exp
    assert "feature_values" in exp
    assert "SHAP_values" in exp
    assert "explanation" in exp
    assert "reason" in exp

    assert isinstance(exp["feature_values"], dict)
    assert isinstance(exp["SHAP_values"], dict)
    assert len(exp["feature_values"]) > 0
    assert len(exp["SHAP_values"]) > 0


def test_dynamic_explanation_formatting(sample_feature_df):
    acct_id = "ACC_0000"
    exp = explain_account(acct_id, sample_feature_df)

    explanation = exp["explanation"]
    assert isinstance(explanation, str)
    assert "Risk is elevated primarily because of:" in explanation or "Risk is low primarily because of:" in explanation

    lines = explanation.split("\n")
    assert len(lines) >= 2
    # Verify numbered list format "1. ..."
    assert lines[1].startswith("1. ")


def test_explain_flagged_accounts(sample_feature_df):
    flagged_explanations = explain_flagged_accounts(sample_feature_df, min_risk_score=30.0)

    assert isinstance(flagged_explanations, list)
    for exp in flagged_explanations:
        assert exp["risk_score"] >= 30.0
        assert "account_id" in exp
        assert "top_positive_features" in exp
        assert "top_negative_features" in exp
        assert "feature_values" in exp
        assert "SHAP_values" in exp
        assert "explanation" in exp
