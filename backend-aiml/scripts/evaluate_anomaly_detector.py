"""
scripts/evaluate_anomaly_detector.py
=====================================
Evaluates the unsupervised Isolation Forest anomaly detection engine on PaySim data.

Outputs:
  - Anomaly score metrics & distribution report
  - Statistical comparison between legitimate and mule accounts
  - JSON report saved to backend-aiml/reports/anomaly_detection_report.json
"""

from __future__ import annotations

import json
import logging
import pathlib
import sys
import time

import pandas as pd

# Setup PYTHONPATH
BASE_DIR = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.services.anomaly_detector import (
    AccountAnomalyDetector,
    evaluate_anomaly_scores_vs_labels,
)
from app.services.feature_pipeline import build_feature_matrix

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_anomaly_evaluation(
    dataset_path: str = "PS_20174392719_1491204439457_log.csv",
    sample_rows: int = 50000,
) -> dict:
    t0 = time.perf_counter()
    logger.info("Extracting feature matrix from PaySim dataset (%d rows)...", sample_rows)

    from app.services.preprocessing_pipeline import preprocess_transactions
    from app.services.features_velocity import compute_velocity_features
    from app.services.features_behavioral import compute_behavioral_features
    from app.services.features_graph import compute_graph_features
    from app.services.features_anomaly import compute_anomaly_features
    from app.services.features_mule_flow import compute_mule_flow_features
    from app.services.features_temporal_change import compute_temporal_change_features

    clean_df, _, _ = preprocess_transactions(dataset_path, max_rows=sample_rows)
    has_label = "is_mule_pattern" in clean_df.columns

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
        .fillna(0.0)
    )

    if has_label:
        label_map = clean_df.groupby("sender_account_id")["is_mule_pattern"].max().reset_index().rename(columns={"sender_account_id": "account_id"})
        recv_map = clean_df.groupby("receiver_account_id")["is_mule_pattern"].max().reset_index().rename(columns={"receiver_account_id": "account_id"})
        all_labels = pd.concat([label_map, recv_map]).groupby("account_id")["is_mule_pattern"].max().reset_index()
        feat_df = feat_df.merge(all_labels, on="account_id", how="left").fillna(0)
        labels = feat_df["is_mule_pattern"].values
    else:
        labels = None

    # 2. Fit Unsupervised Isolation Forest Anomaly Detector
    logger.info("Fitting unsupervised Isolation Forest model (contamination=0.01)...")
    detector = AccountAnomalyDetector(contamination=0.01, random_state=42)

    if has_label:
        # Tune contamination using validation methodology
        detector.fit(feat_df, tune_contamination_with_val=True, y_val=labels)
    else:
        detector.fit(feat_df)

    # 3. Predict Anomaly Scores, Flags, and Percentiles
    anomaly_df = detector.predict_anomalies(feat_df)

    # 4. Statistical Evaluation vs Labels if present
    if has_label and labels is not None:
        eval_metrics = evaluate_anomaly_scores_vs_labels(anomaly_df, labels)
    else:
        eval_metrics = {"message": "Ground-truth labels unavailable (pure unsupervised mode)"}

    # Summary report
    anom_count = int((anomaly_df["anomaly_flag"] == 1).sum())
    report = {
        "dataset": dataset_path,
        "sample_rows_ingested": sample_rows,
        "unique_accounts": len(anomaly_df),
        "anomalous_accounts_flagged": anom_count,
        "anomaly_flag_rate": round(anom_count / max(len(anomaly_df), 1), 6),
        "contamination_setting": detector.contamination,
        "anomaly_score_stats": {
            "mean": round(float(anomaly_df["anomaly_score"].mean()), 4),
            "median": round(float(anomaly_df["anomaly_score"].median()), 4),
            "std": round(float(anomaly_df["anomaly_score"].std()), 4),
            "max": round(float(anomaly_df["anomaly_score"].max()), 4),
            "min": round(float(anomaly_df["anomaly_score"].min()), 4),
        },
        "statistical_label_evaluation": eval_metrics,
        "top_10_anomalous_accounts": anomaly_df.sort_values("anomaly_score", ascending=False).head(10).to_dict(orient="records"),
        "elapsed_seconds": round(time.perf_counter() - t0, 3),
    }

    # Save JSON report
    report_path = BASE_DIR / "backend-aiml" / "reports" / "anomaly_detection_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info("Saved anomaly detection report to '%s'", report_path)
    return report


if __name__ == "__main__":
    rep = run_anomaly_evaluation()
    print("\n=== ANOMALY DETECTION EVALUATION REPORT ===")
    print(json.dumps(rep, indent=2))
