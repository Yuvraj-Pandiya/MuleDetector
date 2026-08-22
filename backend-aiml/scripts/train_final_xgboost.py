"""
scripts/train_final_xgboost.py
================================
Final XGBoost Classifier Training Script for MuleDetector.

Trains the final XGBoost classifier with:
  - Dynamic class imbalance scale_pos_weight
  - Validation-only hyperparameter tuning
  - Early stopping
  - Persisting model.pkl, metrics.json, feature_schema.json,
    training_metadata.json, and preprocessing_config.json
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

from app.services.model_trainer import (
    FEATURE_SCHEMA_PATH,
    METRICS_PATH,
    MODEL_PATH,
    PREPROCESSING_CONFIG_PATH,
    TRAINING_METADATA_PATH,
    train_model,
)
from app.services.mock_generator import generate_mock_features_csv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_final_training(
    dataset_path: str = "PS_20174392719_1491204439457_log.csv",
    sample_rows: int = 50000,
) -> dict:
    t0 = time.perf_counter()
    logger.info("[TrainPipeline] Starting final XGBoost training script...")

    csv_file = BASE_DIR / dataset_path
    feat_df: pd.DataFrame

    if csv_file.exists():
        logger.info("[TrainPipeline] Ingesting PaySim dataset (%d rows)...", sample_rows)
        from app.services.preprocessing_pipeline import preprocess_transactions
        from app.services.features_velocity import compute_velocity_features
        from app.services.features_behavioral import compute_behavioral_features
        from app.services.features_graph import compute_graph_features
        from app.services.features_anomaly import compute_anomaly_features
        from app.services.features_mule_flow import compute_mule_flow_features
        from app.services.features_temporal_change import compute_temporal_change_features

        clean_df, _, _ = preprocess_transactions(str(csv_file), max_rows=sample_rows)
        has_label = "is_mule_pattern" in clean_df.columns

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
        logger.info("[TrainPipeline] PaySim dataset not found at %s. Generating mock features...", csv_file)
        feat_df = generate_mock_features_csv()
        if "first_transaction_time" not in feat_df.columns:
            start_date = pd.Timestamp("2026-01-01 00:00:00")
            time_steps = [start_date + pd.Timedelta(hours=i) for i in range(len(feat_df))]
            feat_df["first_transaction_time"] = time_steps

    if "is_mule_pattern" not in feat_df.columns:
        feat_df["is_mule_pattern"] = 0
        feat_df.iloc[:50, feat_df.columns.get_loc("is_mule_pattern")] = 1

    logger.info("[TrainPipeline] Triggering train_model on %d rows...", len(feat_df))
    metrics = train_model(feat_df, label_col="is_mule_pattern")

    # Copy artifacts to backend-aiml/reports/
    reports_dir = BASE_DIR / "backend-aiml" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy(MODEL_PATH, reports_dir / "model.pkl")
    shutil.copy(METRICS_PATH, reports_dir / "metrics.json")
    shutil.copy(FEATURE_SCHEMA_PATH, reports_dir / "feature_schema.json")
    shutil.copy(TRAINING_METADATA_PATH, reports_dir / "training_metadata.json")
    shutil.copy(PREPROCESSING_CONFIG_PATH, reports_dir / "preprocessing_config.json")

    logger.info("[TrainPipeline] All 5 artifacts persisted and copied to backend-aiml/reports/")
    return metrics


if __name__ == "__main__":
    result_metrics = run_final_training()
    print("\n=======================================================")
    print("      FINAL XGBOOST CLASSIFIER TRAINING COMPLETE        ")
    print("=======================================================")
    print(f"Model Type       : {result_metrics.get('model_type')}")
    print(f"Training Time    : {result_metrics.get('training_time_seconds')}s")
    print(f"Precision        : {result_metrics.get('precision')}")
    print(f"Recall           : {result_metrics.get('recall')}")
    print(f"F1-Score         : {result_metrics.get('f1')}")
    print(f"ROC-AUC          : {result_metrics.get('roc_auc')}")
    print(f"PR-AUC           : {result_metrics.get('pr_auc')}")
    print(f"Scale Pos Weight : {result_metrics.get('scale_pos_weight')} (Learned from train fold)")
    print(f"Confusion Matrix : {result_metrics.get('confusion_matrix')}")

    print("\n--- PERSISTED ARTIFACTS ---")
    print("  1. Model Binary      : backend/app/data/model.pkl")
    print("  2. Test Metrics      : backend/app/data/metrics.json")
    print("  3. Feature Schema    : backend/app/data/feature_schema.json")
    print("  4. Training Metadata : backend/app/data/training_metadata.json")
    print("  5. Preprocessing Config: backend/app/data/preprocessing_config.json")
    print("=======================================================\n")
