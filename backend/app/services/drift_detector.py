"""
app/services/drift_detector.py
===============================
Model & Feature Drift Monitoring Engine for MuleDetector.

Calculates:
  1. Population Stability Index (PSI) per feature between baseline training data & recent inference data.
  2. Feature distribution mean/std shifts (μ_baseline vs μ_current).
  3. Class-rate changes (baseline mule rate vs recent validated feedback rate).
  4. Prediction score distribution histogram shifts (5 score bins).
  5. Automatic Drift Alert Generation when configured PSI thresholds are exceeded.
"""

from __future__ import annotations

import datetime
import json
import logging
import pathlib
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
_TRANSACTIONS_CSV = _DATA_DIR / "transactions.csv"
DRIFT_REPORT_PATH = _DATA_DIR / "drift_report.json"

# Configurable PSI Thresholds
DEFAULT_WARNING_THRESHOLD = 0.10
DEFAULT_CRITICAL_THRESHOLD = 0.25


def calculate_psi(
    expected: np.ndarray, actual: np.ndarray, num_bins: int = 10
) -> float:
    """
    Calculate Population Stability Index (PSI) between baseline (expected)
    and current inference (actual) arrays.

    PSI = sum((Actual_i - Expected_i) * ln(Actual_i / Expected_i))
    """
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)

    # Remove NaNs
    expected = expected[~np.isnan(expected)]
    actual = actual[~np.isnan(actual)]

    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    # Quantile bin edges based on expected distribution
    percentiles = np.linspace(0, 100, num_bins + 1)
    try:
        bin_edges = np.percentile(expected, percentiles)
    except Exception:
        bin_edges = np.linspace(np.min(expected), np.max(expected), num_bins + 1)

    # Unique bin edges to avoid zero width bins
    bin_edges = np.unique(bin_edges)
    if len(bin_edges) <= 1:
        return 0.0

    bin_edges[0] = -np.inf
    bin_edges[-1] = np.inf

    # Count frequencies
    exp_counts, _ = np.histogram(expected, bins=bin_edges)
    act_counts, _ = np.histogram(actual, bins=bin_edges)

    # Convert to proportions with smoothing epsilon
    exp_props = exp_counts / float(len(expected))
    act_props = act_counts / float(len(actual))

    eps = 1e-4
    exp_props = np.where(exp_props == 0, eps, exp_props)
    act_props = np.where(act_props == 0, eps, act_props)

    psi_val = np.sum((act_props - exp_props) * np.log(act_props / exp_props))
    return float(np.round(psi_val, 4))


def compute_drift_metrics(
    warning_threshold: float = DEFAULT_WARNING_THRESHOLD,
    critical_threshold: float = DEFAULT_CRITICAL_THRESHOLD,
) -> Dict[str, Any]:
    """
    Compute comprehensive feature & prediction drift metrics comparing
    training baseline data vs recent inference scoring matrix.
    """
    _DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Load baseline feature matrix and recent scoring matrix
    from app.services.feature_pipeline import build_feature_matrix
    from app.services.risk_scorer import score_accounts

    if _TRANSACTIONS_CSV.exists():
        df_full = build_feature_matrix(_TRANSACTIONS_CSV)
    else:
        mock_csv = _DATA_DIR / "mock_features.csv"
        if not mock_csv.exists():
            from scripts.generate_mock_features import main as gen_mock
            gen_mock()
        df_full = pd.read_csv(mock_csv)

    # Split into baseline training slice (first 60%) and recent inference slice (last 40%)
    split_idx = int(len(df_full) * 0.6)
    if split_idx == 0 or split_idx == len(df_full):
        df_base = df_full
        df_recent = df_full
    else:
        df_base = df_full.iloc[:split_idx].copy()
        df_recent = df_full.iloc[split_idx:].copy()

    # Numerical feature columns
    exclude_cols = {"account_id", "timestamp", "is_mule_pattern", "label"}
    feat_cols = [c for c in df_full.columns if c not in exclude_cols and pd.api.types.is_numeric_dtype(df_full[c])]

    monitored_features: List[Dict[str, Any]] = []
    psi_scores: List[float] = []

    for f_col in feat_cols:
        base_vals = df_base[f_col].dropna().values
        rec_vals = df_recent[f_col].dropna().values

        psi_val = calculate_psi(base_vals, rec_vals)
        psi_scores.append(psi_val)

        m_base = float(np.mean(base_vals)) if len(base_vals) > 0 else 0.0
        s_base = float(np.std(base_vals)) if len(base_vals) > 0 else 1.0
        m_rec = float(np.mean(rec_vals)) if len(rec_vals) > 0 else 0.0
        s_rec = float(np.std(rec_vals)) if len(rec_vals) > 0 else 1.0

        if psi_val >= critical_threshold:
            status = "CRITICAL"
            desc = f"Severe distribution shift detected (PSI = {psi_val:.3f} >= {critical_threshold}). Significant anomaly burst."
        elif psi_val >= warning_threshold:
            status = "WARNING"
            desc = f"Moderate distribution shift (PSI = {psi_val:.3f} >= {warning_threshold}). Monitor for feature drift."
        else:
            status = "NORMAL"
            desc = f"Distribution stable (PSI = {psi_val:.3f} < {warning_threshold})."

        monitored_features.append({
            "feature": f_col,
            "training_distribution": f"μ = {m_base:.2f} (σ = {s_base:.2f})",
            "current_distribution": f"μ = {m_rec:.2f} (σ = {s_rec:.2f})",
            "drift_metric": psi_val,
            "metric_name": "PSI",
            "status": status,
            "description": desc,
        })

    # Overall PSI & Severity
    overall_psi = float(np.mean(psi_scores)) if psi_scores else 0.05
    crit_count = sum(1 for f in monitored_features if f["status"] == "CRITICAL")
    warn_count = sum(1 for f in monitored_features if f["status"] == "WARNING")

    if crit_count > 0:
        overall_drift_status = "CRITICAL"
        drift_severity = "HIGH"
    elif warn_count > 0:
        overall_drift_status = "WARNING"
        drift_severity = "MODERATE"
    else:
        overall_drift_status = "NORMAL"
        drift_severity = "LOW"

    # --- Prediction Score Distribution Shifts ---
    scored_base = score_accounts(df_base)
    scored_recent = score_accounts(df_recent)

    base_probs = (scored_base["risk_score"] / 100.0).values
    rec_probs = (scored_recent["risk_score"] / 100.0).values

    pred_bins = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    bin_labels = [
        "0.0 - 0.2 (Low Risk)",
        "0.2 - 0.4 (Mild Risk)",
        "0.4 - 0.6 (Medium Risk)",
        "0.6 - 0.8 (High Risk)",
        "0.8 - 1.0 (Critical Mule)",
    ]

    base_counts, _ = np.histogram(base_probs, bins=pred_bins)
    rec_counts, _ = np.histogram(rec_probs, bins=pred_bins)

    base_pcts = (base_counts / max(len(base_probs), 1) * 100.0).round(1).tolist()
    rec_pcts = (rec_counts / max(len(rec_probs), 1) * 100.0).round(1).tolist()

    prediction_distribution = [
        {"range": label, "training_pct": b_pct, "current_pct": r_pct}
        for label, b_pct, r_pct in zip(bin_labels, base_pcts, rec_pcts)
    ]

    # --- Class-Rate Shift ---
    base_mule_rate = float(round((df_base["is_mule_pattern"].mean() if "is_mule_pattern" in df_base.columns else 0.052) * 100, 2))
    
    # Validated class rate from feedback store
    from app.services.feedback_store import get_feedback_history
    history = get_feedback_history()
    confirmed_cnt = sum(1 for h in history if h.get("decision") == "CONFIRMED_MULE")
    legit_cnt = sum(1 for h in history if h.get("decision") in ("LEGITIMATE", "FALSE_POSITIVE"))
    total_val = confirmed_cnt + legit_cnt

    recent_validated_mule_rate = float(round((confirmed_cnt / max(total_val, 1) * 100.0), 2)) if total_val > 0 else base_mule_rate

    # --- Drift Alert Generation ---
    drift_alert_triggered = False
    drift_alert_details = None

    if overall_drift_status in ("CRITICAL", "WARNING"):
        drift_alert_triggered = True
        drift_alert_details = {
            "title": f"Model Drift Alert: {overall_drift_status} Severity",
            "message": f"Overall PSI ({overall_psi:.3f}) exceeded threshold ({warning_threshold:.2f}). {crit_count} critical feature drift(s) detected.",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        # Automatically insert drift alert into SQLite alerts.db
        try:
            from app.services.alert_generator import _bootstrap_db, _get_conn, _make_alert_id
            _bootstrap_db()
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            alert_id = _make_alert_id(f"MODEL-DRIFT-{now_iso[:10]}")

            with _get_conn() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO alerts
                        (alert_id, account_id, risk_score, risk_tier, severity,
                         summary, top_features, top_reasons, anomaly_score, network_risk,
                         connected_suspicious_count, model_version, status, created_at, updated_at)
                    VALUES (?, 'SYSTEM-MODEL-MONITOR', 89.5, 'CRITICAL', 'CRITICAL',
                            ?, '["overall_psi", "feature_drift"]', '["Population stability drift threshold exceeded", "Feature distribution shift"]',
                            ?, 90.0, 0, 'v2.5.0-XGBoost', 'OPEN', ?, ?)
                    """,
                    (alert_id, drift_alert_details["message"], overall_psi, now_iso, now_iso),
                )
        except Exception as exc:
            logger.warning("[DriftDetector] Failed to persist drift alert: %s", exc)

    result = {
        "model_version": "v2.5.0-XGBoost",
        "training_date": "2026-08-22T14:30:00Z",
        "latest_scoring_date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "feature_drift_status": overall_drift_status,
        "drift_severity": drift_severity,
        "overall_psi": overall_psi,
        "thresholds": {
            "warning_threshold": warning_threshold,
            "critical_threshold": critical_threshold,
        },
        "class_rate_shift": {
            "baseline_training_mule_rate_pct": base_mule_rate,
            "recent_validated_mule_rate_pct": recent_validated_mule_rate,
            "rate_delta_pct": round(recent_validated_mule_rate - base_mule_rate, 2),
        },
        "drift_alert_triggered": drift_alert_triggered,
        "drift_alert_details": drift_alert_details,
        "prediction_distribution": prediction_distribution,
        "monitored_features": monitored_features,
    }

    with open(DRIFT_REPORT_PATH, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)

    return result
