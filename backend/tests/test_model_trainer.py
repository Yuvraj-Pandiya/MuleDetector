"""
tests/test_model_trainer.py
============================
Unit test suite for model_trainer module and XGBoost classifier artifact persistence.
"""

from __future__ import annotations

import json
import pathlib
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import numpy as np
import pandas as pd
import pytest

from app.services.model_trainer import (
    FEATURE_SCHEMA_PATH,
    METRICS_PATH,
    MODEL_PATH,
    PREPROCESSING_CONFIG_PATH,
    TRAINING_METADATA_PATH,
    train_model,
)


@pytest.fixture
def sample_feature_matrix():
    """Generates a synthetic feature matrix with 200 samples and explicit labels."""
    np.random.seed(42)
    n_samples = 200

    is_mule = np.zeros(n_samples, dtype=int)
    is_mule[::5] = 1  # 20% positive class imbalance

    velocity_5m = np.random.poisson(lam=2, size=n_samples) + is_mule * 10
    amount_max = np.random.exponential(scale=500, size=n_samples) + is_mule * 5000
    mule_flow_ratio = np.random.uniform(0, 0.2, size=n_samples) + is_mule * 0.7
    pagerank = np.random.uniform(0.001, 0.01, size=n_samples) + is_mule * 0.05

    start_time = pd.Timestamp("2026-01-01 00:00:00")
    timestamps = [start_time + pd.Timedelta(hours=i) for i in range(n_samples)]

    df = pd.DataFrame({
        "account_id": [f"ACC_{i:04d}" for i in range(n_samples)],
        "first_transaction_time": timestamps,
        "velocity_5m": velocity_5m,
        "amount_max": amount_max,
        "mule_flow_ratio": mule_flow_ratio,
        "pagerank": pagerank,
        "is_mule_pattern": is_mule,
    })
    return df


def test_train_model_xgboost_execution(sample_feature_matrix):
    metrics = train_model(sample_feature_matrix, label_col="is_mule_pattern")

    assert metrics["unsupervised"] is False
    assert metrics["model_type"] == "XGBClassifier"
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1" in metrics
    assert "roc_auc" in metrics
    assert "pr_auc" in metrics
    assert "confusion_matrix" in metrics
    assert len(metrics["confusion_matrix"]) == 2


def test_artifacts_persistence(sample_feature_matrix):
    train_model(sample_feature_matrix, label_col="is_mule_pattern")

    assert MODEL_PATH.exists()
    assert METRICS_PATH.exists()
    assert FEATURE_SCHEMA_PATH.exists()
    assert TRAINING_METADATA_PATH.exists()
    assert PREPROCESSING_CONFIG_PATH.exists()

    with open(METRICS_PATH, "r", encoding="utf-8") as f:
        metrics = json.load(f)
    assert metrics["model_type"] == "XGBClassifier"

    with open(FEATURE_SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)
    assert "feature_columns" in schema
    assert "feature_types" in schema
    assert "feature_importance_ranking" in schema
    assert len(schema["feature_importance_ranking"]) > 0

    with open(TRAINING_METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    assert "model_version" in metadata
    assert "training_date" in metadata
    assert "best_hyperparameters" in metadata
    assert "early_stopping_best_iteration" in metadata
    assert "learned_class_imbalance" in metadata

    with open(PREPROCESSING_CONFIG_PATH, "r", encoding="utf-8") as f:
        prep = json.load(f)
    assert "missing_value_imputation" in prep
    assert "point_in_time_causality_enforced" in prep


def test_dynamic_class_imbalance_handling(sample_feature_matrix):
    train_model(sample_feature_matrix, label_col="is_mule_pattern")

    with open(TRAINING_METADATA_PATH, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    imb = metadata["learned_class_imbalance"]
    assert "scale_pos_weight" in imb
    assert imb["scale_pos_weight"] > 0
    assert "synthetic assumptions" in imb["source"].lower() or "calculated directly" in imb["source"].lower()


def test_unsupervised_fallback(sample_feature_matrix):
    no_label_df = sample_feature_matrix.drop(columns=["is_mule_pattern"])
    metrics = train_model(no_label_df, label_col="non_existent_label")

    assert metrics["unsupervised"] is True
    assert metrics["model_type"] == "IsolationForest"
    assert MODEL_PATH.exists()
    assert METRICS_PATH.exists()
