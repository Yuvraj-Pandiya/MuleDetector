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

from app.services.model_benchmarker import ModelBenchmarker, run_model_benchmark


@pytest.fixture
def sample_feature_matrix():
    """Generates a synthetic feature matrix with 200 samples and explicit labels."""
    np.random.seed(42)
    n_samples = 200

    # Normal vs Mule features
    is_mule = np.zeros(n_samples, dtype=int)
    is_mule[::6] = 1  # ~16% positive class imbalance distributed across timestamps

    velocity_5m = np.random.poisson(lam=2, size=n_samples) + is_mule * 10
    amount_max = np.random.exponential(scale=500, size=n_samples) + is_mule * 5000
    mule_flow_ratio = np.random.uniform(0, 0.2, size=n_samples) + is_mule * 0.7
    pagerank = np.random.uniform(0.001, 0.01, size=n_samples) + is_mule * 0.05

    df = pd.DataFrame({
        "account_id": [f"ACC_{i:04d}" for i in range(n_samples)],
        "velocity_5m": velocity_5m,
        "amount_max": amount_max,
        "mule_flow_ratio": mule_flow_ratio,
        "pagerank": pagerank,
        "is_mule_pattern": is_mule,
    })
    return df


def test_model_benchmarker_runs_successfully(sample_feature_matrix, tmp_path):
    benchmarker = ModelBenchmarker(data_dir=tmp_path)
    res = benchmarker.run(sample_feature_matrix, label_col="is_mule_pattern")

    assert res["status"] == "success"
    assert "best_model" in res
    assert len(res["models_evaluated"]) == 3
    assert "Logistic Regression" in res["models_evaluated"]
    assert "Random Forest" in res["models_evaluated"]
    assert "XGBoost" in res["models_evaluated"]


def test_artifacts_created(sample_feature_matrix, tmp_path):
    benchmarker = ModelBenchmarker(data_dir=tmp_path)
    res = benchmarker.run(sample_feature_matrix, label_col="is_mule_pattern")

    csv_path = pathlib.Path(res["artifacts"]["model_comparison_csv"])
    chart_path = pathlib.Path(res["artifacts"]["model_comparison_chart"])
    report_path = pathlib.Path(res["artifacts"]["model_benchmark_report"])

    assert csv_path.exists()
    assert chart_path.exists()
    assert report_path.exists()

    df_csv = pd.read_csv(csv_path)
    assert len(df_csv) == 3
    expected_cols = {"model_name", "precision", "recall", "f1_score", "roc_auc", "pr_auc", "tn", "fp", "fn", "tp", "is_recommended"}
    assert expected_cols.issubset(set(df_csv.columns))


def test_metrics_and_tradeoffs(sample_feature_matrix, tmp_path):
    benchmarker = ModelBenchmarker(data_dir=tmp_path)
    benchmarker.run(sample_feature_matrix, label_col="is_mule_pattern")

    with open(benchmarker.report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    assert "model_results" in report
    assert len(report["model_results"]) == 3

    for model_res in report["model_results"]:
        assert 0.0 <= model_res["precision"] <= 1.0
        assert 0.0 <= model_res["recall"] <= 1.0
        assert 0.0 <= model_res["f1_score"] <= 1.0
        assert 0.0 <= model_res["roc_auc"] <= 1.0
        assert 0.0 <= model_res["pr_auc"] <= 1.0
        assert model_res["tn"] >= 0
        assert model_res["fp"] >= 0
        assert model_res["fn"] >= 0
        assert model_res["tp"] >= 0

        # Threshold tradeoffs
        tradeoffs = model_res["threshold_tradeoffs"]
        assert len(tradeoffs) == 9  # Cutoffs 0.1 to 0.9
        assert tradeoffs[0]["threshold"] == 0.1
        assert tradeoffs[-1]["threshold"] == 0.9


def test_best_model_recommendation_logic(sample_feature_matrix, tmp_path):
    benchmarker = ModelBenchmarker(data_dir=tmp_path)
    benchmarker.run(sample_feature_matrix, label_col="is_mule_pattern")

    with open(benchmarker.report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    rec = report["best_model_recommendation"]
    assert rec["recommended_model"] in ["Logistic Regression", "Random Forest", "XGBoost"]
    assert rec["selection_metric"] == "PR-AUC (Precision-Recall Area Under Curve)"
    assert "Accuracy is explicitly rejected" in rec["rationale"]


def test_unsupervised_label_fallback(sample_feature_matrix, tmp_path):
    # Remove label column to trigger Isolation Forest proxy label resolution
    no_label_df = sample_feature_matrix.drop(columns=["is_mule_pattern"])
    benchmarker = ModelBenchmarker(data_dir=tmp_path)
    res = benchmarker.run(no_label_df, label_col="non_existent_label")

    assert res["status"] == "success"
    with open(benchmarker.report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    assert report["supervised_label_used"] is False


def test_temporal_validation_split(sample_feature_matrix, tmp_path):
    # Add explicit timestamp column
    start_time = pd.Timestamp("2026-01-01 00:00:00")
    sample_feature_matrix["first_transaction_time"] = [
        start_time + pd.Timedelta(hours=i) for i in range(len(sample_feature_matrix))
    ]

    benchmarker = ModelBenchmarker(data_dir=tmp_path)
    res = benchmarker.run(sample_feature_matrix, label_col="is_mule_pattern", split_strategy="temporal")

    assert res["status"] == "success"
    assert res["split_strategy"] == "temporal"
    assert "temporal_periods" in res
    assert "train_period" in res["temporal_periods"]
    assert "validation_period" in res["temporal_periods"]
    assert "test_period" in res["temporal_periods"]

    # Verify chronological ordering (train_end <= val_start and val_end <= test_start)
    train_end = pd.to_datetime(res["temporal_periods"]["train_period"]["end"])
    val_start = pd.to_datetime(res["temporal_periods"]["validation_period"]["start"])
    val_end = pd.to_datetime(res["temporal_periods"]["validation_period"]["end"])
    test_start = pd.to_datetime(res["temporal_periods"]["test_period"]["start"])

    assert train_end <= val_start
    assert val_end <= test_start

    # Verify class distribution reporting
    assert "class_distribution" in res
    assert "train" in res["class_distribution"]
    assert "validation" in res["class_distribution"]
    assert "test" in res["class_distribution"]

    # Verify dataset limitations
    assert "dataset_temporal_limitations" in res
    assert len(res["dataset_temporal_limitations"]) >= 1


def test_run_model_benchmark_wrapper(sample_feature_matrix, tmp_path):
    res = run_model_benchmark(sample_feature_matrix, label_col="is_mule_pattern", data_dir=tmp_path)
    assert res["status"] == "success"
