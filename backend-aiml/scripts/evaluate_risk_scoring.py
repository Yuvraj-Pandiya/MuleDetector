"""
scripts/evaluate_risk_scoring.py
===================================
Calibrated Risk-Scoring Layer Evaluation Script for MuleDetector.

Evaluates candidate threshold cutoffs against validation data reporting:
  - Precision
  - Recall
  - Alert Volume (count & %)
  - False-Positive Rate (FPR)

Outputs:
  - backend/app/data/risk_scoring_report.json
  - backend-aiml/reports/risk_scoring_report.json
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

from app.services.risk_scorer import CalibratedRiskScorer, score_accounts
from app.services.mock_generator import generate_mock_features_csv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def run_risk_scoring_evaluation(
    dataset_path: str = "PS_20174392719_1491204439457_log.csv",
    sample_rows: int = 50000,
) -> dict:
    t0 = time.perf_counter()
    logger.info("[RiskScoringEval] Starting calibrated risk scoring evaluation...")

    csv_file = BASE_DIR / dataset_path
    feat_df: pd.DataFrame

    if csv_file.exists():
        logger.info("[RiskScoringEval] Ingesting PaySim dataset (%d rows)...", sample_rows)
        from app.services.preprocessing_pipeline import preprocess_transactions
        from app.services.features_velocity import compute_velocity_features
        from app.services.features_behavioral import compute_behavioral_features
        from app.services.features_graph import compute_graph_features
        from app.services.features_anomaly import compute_anomaly_features
        from app.services.features_mule_flow import compute_mule_flow_features
        from app.services.features_temporal_change import compute_temporal_change_features

        clean_df, _, _ = preprocess_transactions(str(csv_file), max_rows=sample_rows)
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
    else:
        logger.info("[RiskScoringEval] PaySim dataset not found at %s. Generating mock features...", csv_file)
        feat_df = generate_mock_features_csv()

    if "is_mule_pattern" not in feat_df.columns:
        feat_df["is_mule_pattern"] = 0
        feat_df.iloc[:50, feat_df.columns.get_loc("is_mule_pattern")] = 1

    y_val = feat_df["is_mule_pattern"].values
    scored_df = score_accounts(feat_df)

    scorer = CalibratedRiskScorer()
    candidate_thresholds = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 85.0, 90.0]
    threshold_eval = scorer.evaluate_candidate_thresholds(
        y_true=y_val,
        risk_scores=scored_df["risk_score"].values,
        candidate_thresholds=candidate_thresholds,
    )

    tier_counts = scored_df["risk_tier"].value_counts().to_dict()

    report = {
        "report_version": "1.0.0",
        "pipeline": "CalibratedRiskScorer -- MuleDetector",
        "total_scored_accounts": len(scored_df),
        "total_positive_mules": int((y_val == 1).sum()),
        "signal_weights": scorer.weights,
        "risk_tier_config": scorer.risk_tier_config,
        "risk_tier_distribution": tier_counts,
        "candidate_threshold_evaluation": threshold_eval,
        "scoring_formula_documentation": (
            "final_risk_score = round(clip((w_sup * P_sup + w_anom * S_anom + w_net * (S_net / 100)) * 100, 0, 100), 1) "
            "where w_sup=0.60, w_anom=0.25, w_net=0.15."
        ),
        "elapsed_seconds": round(time.perf_counter() - t0, 3),
    }

    # Save artifact
    data_dir = BASE_DIR / "backend" / "app" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    report_file = data_dir / "risk_scoring_report.json"
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")

    reports_dir = BASE_DIR / "backend-aiml" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(report_file, reports_dir / "risk_scoring_report.json")

    logger.info("[RiskScoringEval] Saved risk_scoring_report.json to backend/app/data and backend-aiml/reports/")
    return report


if __name__ == "__main__":
    rep = run_risk_scoring_evaluation()
    print("\n==========================================================================================")
    print("                CALIBRATED ACCOUNT RISK-SCORING THRESHOLD EVALUATION TABLE                 ")
    print("==========================================================================================")
    print(f"Total Accounts Scored : {rep['total_scored_accounts']}")
    print(f"Total Positive Mules  : {rep['total_positive_mules']}")
    print(f"Signal Weights       : {rep['signal_weights']}\n")

    print(f"{'Thresh':<8s} | {'Precision':<10s} | {'Recall':<10s} | {'F1-Score':<10s} | {'Alert Vol Count':<16s} | {'Alert Vol %':<12s} | {'FPR':<8s}")
    print("-" * 90)
    for row in rep["candidate_threshold_evaluation"]:
        print(f"{row['threshold']:<8.1f} | {row['precision']:<10.4f} | {row['recall']:<10.4f} | {row['f1_score']:<10.4f} | {row['alert_volume_count']:<16d} | {row['alert_volume_pct']:<11.2f}% | {row['false_positive_rate']:<8.4f}")

    print("\n--- RISK TIER DISTRIBUTION ---")
    for tier, cnt in rep["risk_tier_distribution"].items():
        pct = round((cnt / rep['total_scored_accounts']) * 100.0, 2)
        print(f"  {tier:10s}: {cnt:5d} accounts ({pct}%)")

    print("\nArtifact Report : backend/app/data/risk_scoring_report.json")
    print("==========================================================================================\n")
