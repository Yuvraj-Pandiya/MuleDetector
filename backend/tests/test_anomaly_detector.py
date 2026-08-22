"""
tests/test_anomaly_detector.py
================================
Unit tests for the unsupervised Isolation Forest anomaly detection layer.
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import numpy as np
import pandas as pd
import pytest

from app.services.anomaly_detector import (
    AccountAnomalyDetector,
    evaluate_anomaly_scores_vs_labels,
)


@pytest.fixture
def sample_feature_matrix() -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Generate synthetic account feature matrix with 100 normal accounts and 5 extreme anomalies.
    """
    np.random.seed(42)

    # 100 normal accounts
    normal_data = {
        "account_id": [f"ACC_NORMAL_{i}" for i in range(100)],
        "txn_count_1h": np.random.poisson(lam=1, size=100),
        "total_amount_out_24h": np.random.uniform(100, 1000, size=100),
        "in_degree": np.random.randint(1, 4, size=100),
        "is_in_short_cycle": np.zeros(100, dtype=int),
    }
    df_normal = pd.DataFrame(normal_data)

    # 5 extreme anomaly accounts (huge transfer volume, massive transaction counts)
    anomaly_data = {
        "account_id": [f"ACC_ANOMALY_{i}" for i in range(5)],
        "txn_count_1h": np.random.randint(50, 100, size=5),
        "total_amount_out_24h": np.random.uniform(500000, 1000000, size=5),
        "in_degree": np.random.randint(20, 50, size=5),
        "is_in_short_cycle": np.ones(5, dtype=int),
    }
    df_anomaly = pd.DataFrame(anomaly_data)

    df_full = pd.concat([df_normal, df_anomaly], ignore_index=True)
    labels = np.array([0] * 100 + [1] * 5)

    return df_full, labels


def test_anomaly_score_output_format(sample_feature_matrix):
    """Verify anomaly_score in [0,1], anomaly_flag, and anomaly_percentile outputs."""
    df_full, _ = sample_feature_matrix

    detector = AccountAnomalyDetector(contamination=0.05, random_state=42)
    detector.fit(df_full)
    preds = detector.predict_anomalies(df_full)

    assert "account_id" in preds.columns
    assert "anomaly_score" in preds.columns
    assert "anomaly_flag" in preds.columns
    assert "anomaly_percentile" in preds.columns

    # Verify anomaly_score range [0.0, 1.0]
    assert (preds["anomaly_score"] >= 0.0).all()
    assert (preds["anomaly_score"] <= 1.0).all()

    # Verify anomaly_percentile range [0.0, 100.0]
    assert (preds["anomaly_percentile"] >= 0.0).all()
    assert (preds["anomaly_percentile"] <= 100.0).all()

    # Verify top anomalies have highest scores
    anomalous_accounts = preds[preds["account_id"].str.contains("ANOMALY")]
    normal_accounts = preds[preds["account_id"].str.contains("NORMAL")]
    assert anomalous_accounts["anomaly_score"].mean() > normal_accounts["anomaly_score"].mean()


def test_unsupervised_training_no_leakage(sample_feature_matrix):
    """Verify training is strictly unsupervised without ground-truth labels."""
    df_full, labels = sample_feature_matrix
    df_with_label = df_full.copy()
    df_with_label["is_mule_pattern"] = labels

    detector = AccountAnomalyDetector(contamination=0.05)
    detector.fit(df_with_label)

    # Ground truth label 'is_mule_pattern' MUST NOT be in model feature names
    assert "is_mule_pattern" not in detector.feature_names
    assert "fraud_label" not in detector.feature_names


def test_contamination_tuning(sample_feature_matrix):
    """Test validation methodology for contamination hyperparameter tuning."""
    df_full, labels = sample_feature_matrix

    detector = AccountAnomalyDetector(contamination=0.10)
    detector.fit(df_full, tune_contamination_with_val=True, y_val=labels)

    assert detector.contamination in [0.001, 0.005, 0.01, 0.02, 0.05, 0.10]


def test_label_evaluation_metrics(sample_feature_matrix):
    """Test evaluate_anomaly_scores_vs_labels metric calculation."""
    df_full, labels = sample_feature_matrix

    detector = AccountAnomalyDetector(contamination=0.05)
    detector.fit(df_full)
    preds = detector.predict_anomalies(df_full)

    metrics = evaluate_anomaly_scores_vs_labels(preds, labels)

    assert metrics["legitimate_count"] == 100
    assert metrics["mule_count"] == 5
    assert metrics["mean_mule_anomaly_score"] > metrics["mean_legitimate_anomaly_score"]
    assert metrics["unsupervised_roc_auc"] > 0.80


def test_model_serialization(tmp_path, sample_feature_matrix):
    """Test saving and loading the anomaly detector model."""
    df_full, _ = sample_feature_matrix

    detector = AccountAnomalyDetector(contamination=0.05)
    detector.fit(df_full)

    save_path = tmp_path / "anomaly_model.pkl"
    detector.save(save_path)
    assert save_path.exists()

    loaded_detector = AccountAnomalyDetector.load(save_path)
    assert loaded_detector.is_fitted

    preds1 = detector.predict_anomalies(df_full)
    preds2 = loaded_detector.predict_anomalies(df_full)

    pd.testing.assert_frame_equal(preds1, preds2)
