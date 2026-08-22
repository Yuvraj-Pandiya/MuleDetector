"""
scripts/benchmark_models.py
==============================
Model Benchmarking Pipeline Script for MuleDetector.

Runs fair comparison across Logistic Regression, Random Forest, and XGBoost models
using identical train/validation/test feature splits.

Outputs:
  - backend/app/data/model_comparison.csv
  - backend/app/data/model_comparison_chart.png
  - backend/app/data/model_benchmark_report.json
  - backend-aiml/reports/model_comparison.csv
  - backend-aiml/reports/model_comparison_chart.png
  - backend-aiml/reports/model_benchmark_report.json
"""

from __future__ import annotations

import json
import logging
import pathlib
import shutil
import sys
import time

import pandas as pd

# Setup PYTHONPATH
BASE_DIR = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.services.model_benchmarker import ModelBenchmarker, run_model_benchmark
from app.services.mock_generator import generate_mock_features_csv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_benchmark_pipeline(
    dataset_path: str = "PS_20174392719_1491204439457_log.csv",
    sample_rows: int = 50000,
) -> dict:
    t0 = time.perf_counter()
    logger.info("[BenchmarkPipeline] Starting benchmark script...")

    csv_file = BASE_DIR / dataset_path
    feat_df: pd.DataFrame

    if csv_file.exists():
        logger.info("[BenchmarkPipeline] Ingesting PaySim dataset (%d rows)...", sample_rows)
        from app.services.preprocessing_pipeline import preprocess_transactions
        from app.services.features_velocity import compute_velocity_features
        from app.services.features_behavioral import compute_behavioral_features
        from app.services.features_graph import compute_graph_features
        from app.services.features_anomaly import compute_anomaly_features
        from app.services.features_mule_flow import compute_mule_flow_features
        from app.services.features_temporal_change import compute_temporal_change_features

        clean_df, _, _ = preprocess_transactions(str(csv_file), max_rows=sample_rows)
        has_label = "is_mule_pattern" in clean_df.columns

        # Account-level timestamp mapping
        time_map = clean_df.groupby("sender_account_id")["timestamp"].min().reset_index().rename(
            columns={"sender_account_id": "account_id", "timestamp": "first_transaction_time"}
        )

        vf = compute_velocity_features(clean_df)
        bf = compute_behavioral_features(clean_df)
        gf = compute_graph_features(clean_df)
        af = compute_anomaly_features(clean_df)
        mf = compute_mule_flow_features(clean_df)
        tc = compute_temporal_change_features(clean_df)

        feat_df = (
            vf
            .merge(bf, on="account_id", how="outer")
            .merge(gf, on="account_id", how="outer")
            .merge(af, on="account_id", how="outer")
            .merge(mf, on="account_id", how="outer")
            .merge(tc, on="account_id", how="outer")
            .merge(time_map, on="account_id", how="left")
            .fillna(0.0)
        )

        if has_label:
            label_map = clean_df.groupby("sender_account_id")["is_mule_pattern"].max().reset_index().rename(columns={"sender_account_id": "account_id"})
            recv_map = clean_df.groupby("receiver_account_id")["is_mule_pattern"].max().reset_index().rename(columns={"receiver_account_id": "account_id"})
            all_labels = pd.concat([label_map, recv_map]).groupby("account_id")["is_mule_pattern"].max().reset_index()
            feat_df = feat_df.merge(all_labels, on="account_id", how="left").fillna(0)
    else:
        logger.info("[BenchmarkPipeline] PaySim dataset not found at %s. Generating mock features...", csv_file)
        feat_df = generate_mock_features_csv()
        if "first_transaction_time" not in feat_df.columns:
            # Generate synthetic chronological timestamps for mock features
            start_date = pd.Timestamp("2026-01-01 00:00:00")
            time_steps = [start_date + pd.Timedelta(hours=i) for i in range(len(feat_df))]
            feat_df["first_transaction_time"] = time_steps

    # Ensure label column exists
    if "is_mule_pattern" not in feat_df.columns:
        feat_df["is_mule_pattern"] = 0
        feat_df.iloc[:50, feat_df.columns.get_loc("is_mule_pattern")] = 1

    logger.info("[BenchmarkPipeline] Running ModelBenchmarker on %d accounts with %d features...", len(feat_df), len(feat_df.columns) - 1)
    
    backend_data_dir = BASE_DIR / "backend" / "app" / "data"
    benchmarker = ModelBenchmarker(data_dir=backend_data_dir)
    res = benchmarker.run(feat_df, label_col="is_mule_pattern", split_strategy="temporal")

    # Copy generated artifacts to backend-aiml/reports/
    reports_dir = BASE_DIR / "backend-aiml" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy(benchmarker.csv_path, reports_dir / "model_comparison.csv")
    shutil.copy(benchmarker.plot_path, reports_dir / "model_comparison_chart.png")
    shutil.copy(benchmarker.report_path, reports_dir / "model_benchmark_report.json")

    logger.info("[BenchmarkPipeline] Benchmark artifacts copied to backend-aiml/reports/")
    return res


if __name__ == "__main__":
    result = run_benchmark_pipeline()
    print("\n=======================================================")
    print("      MODEL BENCHMARKING PIPELINE (TEMPORAL)           ")
    print("=======================================================")
    print(f"Status           : {result['status']}")
    print(f"Split Strategy   : {result['split_strategy'].upper()}")
    print(f"Elapsed Time     : {result['elapsed_seconds']}s")
    print(f"Best Recommended : {result['best_model']}\n")

    print("--- TEMPORAL PERIOD RANGES ---")
    tp = result["temporal_periods"]
    print(f"Train Period     : {tp['train_period']['start']} --> {tp['train_period']['end']}")
    print(f"Validation Period: {tp['validation_period']['start']} --> {tp['validation_period']['end']}")
    print(f"Test Period      : {tp['test_period']['start']} --> {tp['test_period']['end']}\n")

    print("--- CLASS DISTRIBUTIONS ---")
    cd = result["class_distribution"]
    for split_name, dist in cd.items():
        print(f"{split_name.capitalize():10s}: Total={dist['total']:5d} | Mules={dist['positive_mules']:4d} | Legit={dist['negative_legit']:5d} ({dist['mule_percentage']}%)")
    print()

    print("--- DATASET TEMPORAL LIMITATIONS ---")
    for idx, limit in enumerate(result["dataset_temporal_limitations"], 1):
        print(f"  {idx}. {limit}")

    print("\nArtifact CSV     : ", result['artifacts']['model_comparison_csv'])
    print("Artifact Chart   : ", result['artifacts']['model_comparison_chart'])
    print("=======================================================\n")
