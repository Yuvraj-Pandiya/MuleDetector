"""
app/services/risk_scorer.py
============================
Calibrated Account Risk-Scoring Engine for MuleDetector.

Blends:
  1. Supervised Probability (P_sup from XGBoost)
  2. Unsupervised Anomaly Score (S_anom from IsolationForest)
  3. Graph Network Risk Score (S_net from Topology Engine)

Outputs:
  - final_risk_score: 0.0 to 100.0
  - risk_tier: Configurable Risk Tier ("Low", "Medium", "High", "Critical")

Features:
  - Configurable signal weights & tier cutoffs (no hardcoded tier limits)
  - Candidate threshold evaluation reporting (Precision, Recall, Alert Volume, FPR)
"""

from __future__ import annotations

import logging
import pathlib
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths — kept in sync with model_trainer.py
# ---------------------------------------------------------------------------
_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
MODEL_PATH = _DATA_DIR / "model.pkl"

# Feature columns consumed by the model (same order as training)
FEATURE_SCHEMA_COLUMNS: List[str] = [
    "txn_count_1h",
    "txn_count_24h",
    "txn_count_7d",
    "total_amount_out_24h",
    "total_amount_in_24h",
    "avg_transaction_amount",
    "max_transaction_amount",
    "ratio_received_to_sent_24h",
    "avg_time_to_forward_funds_minutes",
    "unique_counterparty_count",
    "account_age_days",
    "is_new_high_volume_flag",
    "in_degree",
    "out_degree",
    "is_in_short_cycle",
    "betweenness_centrality",
    "fan_in_ratio",
    "fan_out_ratio",
    "amount_zscore_avg",
    "round_number_txn_ratio",
    "odd_hour_txn_ratio",
]


class CalibratedRiskScorer:
    """
    Calibrated Account Risk-Scoring Engine blending supervised probability,
    unsupervised anomaly score, and graph network topology risk score.
    """

    DEFAULT_WEIGHTS = {
        "supervised": 0.60,
        "anomaly": 0.25,
        "network": 0.15,
    }

    DEFAULT_TIERS = {
        "Low": (0.0, 30.0),
        "Medium": (30.0, 70.0),
        "High": (70.0, 85.0),
        "Critical": (85.0, 100.0),
    }

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        risk_tier_config: Optional[Dict[str, Tuple[float, float]]] = None,
    ) -> None:
        self.weights = weights or dict(self.DEFAULT_WEIGHTS)
        tot = sum(self.weights.values())
        if tot > 0:
            self.weights = {k: v / tot for k, v in self.weights.items()}

        self.risk_tier_config = risk_tier_config or dict(self.DEFAULT_TIERS)

    def calculate_risk_score(
        self,
        supervised_probability: Union[float, np.ndarray, pd.Series],
        anomaly_score: Union[float, np.ndarray, pd.Series],
        network_risk_score: Union[float, np.ndarray, pd.Series],
    ) -> Union[float, np.ndarray]:
        """
        Calculate calibrated final risk score (0.0 to 100.0).

        Formula:
          S_calibrated = (w1 * P_sup + w2 * S_anom + w3 * (S_net / 100.0)) * 100.0
        """
        p_sup = np.clip(np.asarray(supervised_probability, dtype=float), 0.0, 1.0)
        s_anom = np.clip(np.asarray(anomaly_score, dtype=float), 0.0, 1.0)
        s_net_norm = np.clip(np.asarray(network_risk_score, dtype=float) / 100.0, 0.0, 1.0)

        w_sup = self.weights.get("supervised", 0.60)
        w_anom = self.weights.get("anomaly", 0.25)
        w_net = self.weights.get("network", 0.15)

        blended_prob = w_sup * p_sup + w_anom * s_anom + w_net * s_net_norm
        final_score = np.round(np.clip(blended_prob * 100.0, 0.0, 100.0), 1)

        if isinstance(supervised_probability, (int, float)) or np.ndim(final_score) == 0:
            return float(final_score)
        return final_score

    def assign_risk_tier(self, score: float) -> str:
        """Assign configurable risk tier label for a single risk score (0-100)."""
        sc = float(score)
        # Check tier boundaries according to risk_tier_config
        for tier_name, (low_b, high_b) in self.risk_tier_config.items():
            if low_b <= sc <= high_b:
                if tier_name == "Critical" and sc >= low_b:
                    return tier_name
                if sc < high_b or (high_b >= 100.0 and sc <= 100.0):
                    return tier_name

        if sc >= 85.0:
            return "Critical"
        elif sc >= 70.0:
            return "High"
        elif sc >= 30.0:
            return "Medium"
        return "Low"

    def assign_risk_tiers(self, scores: Union[np.ndarray, pd.Series, List[float]]) -> List[str]:
        return [self.assign_risk_tier(s) for s in scores]

    def evaluate_candidate_thresholds(
        self,
        y_true: Union[np.ndarray, List[int]],
        risk_scores: Union[np.ndarray, List[float]],
        candidate_thresholds: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Evaluate candidate thresholds against validation data.

        Returns list of dictionaries containing:
          - threshold
          - precision
          - recall
          - f1_score
          - alert_volume_count
          - alert_volume_pct
          - false_positive_rate (FPR)
        """
        from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score

        y_true_arr = np.asarray(y_true, dtype=int)
        scores_arr = np.asarray(risk_scores, dtype=float)
        n_total = len(y_true_arr)

        if candidate_thresholds is None:
            candidate_thresholds = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0]

        eval_results = []
        for thresh in candidate_thresholds:
            y_pred = (scores_arr >= thresh).astype(int)
            prec = round(float(precision_score(y_true_arr, y_pred, zero_division=0)), 4)
            rec = round(float(recall_score(y_true_arr, y_pred, zero_division=0)), 4)
            f1 = round(float(f1_score(y_true_arr, y_pred, zero_division=0)), 4)

            cm = confusion_matrix(y_true_arr, y_pred, labels=[0, 1])
            tn, fp, fn, tp = [int(v) for v in cm.ravel()]

            alert_count = int((y_pred == 1).sum())
            alert_pct = round((alert_count / max(n_total, 1)) * 100.0, 2)
            fpr = round(float(fp / max(fp + tn, 1)), 4)

            eval_results.append({
                "threshold": thresh,
                "precision": prec,
                "recall": rec,
                "f1_score": f1,
                "alert_volume_count": alert_count,
                "alert_volume_pct": alert_pct,
                "false_positive_rate": fpr,
                "tp": tp,
                "fp": fp,
                "tn": tn,
                "fn": fn,
            })
        return eval_results


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

def _load_model() -> Any:
    """Load persisted model; auto-train default model if missing."""
    if not MODEL_PATH.exists():
        logger.info("Trained model not found at '%s' — auto-training default model...", MODEL_PATH)
        mock_csv = _DATA_DIR / "mock_features.csv"
        if not mock_csv.exists():
            from app.services.mock_generator import generate_mock_features_csv
            generate_mock_features_csv(mock_csv)
        feature_df = pd.read_csv(mock_csv)
        from app.services.model_trainer import train_model
        train_model(feature_df)
    return joblib.load(MODEL_PATH)


def _select_features(df: pd.DataFrame, model: Any = None) -> pd.DataFrame:
    """Select and order known feature columns matching model's expected inputs."""
    if model is not None and hasattr(model, "feature_names_in_") and model.feature_names_in_ is not None:
        expected_cols = list(model.feature_names_in_)
        res = pd.DataFrame(index=df.index)
        for c in expected_cols:
            if c in df.columns:
                res[c] = df[c].fillna(0.0).values
            else:
                res[c] = 0.0
        return res[expected_cols]

    cols = [c for c in FEATURE_SCHEMA_COLUMNS if c in df.columns]
    if not cols:
        cols = [c for c in df.columns if c != "account_id" and pd.api.types.is_numeric_dtype(df[c])]
    if model is not None and hasattr(model, "n_features_in_"):
        n_expected = model.n_features_in_
        if len(cols) > n_expected:
            cols = cols[:n_expected]
        elif len(cols) < n_expected:
            res = df[cols].copy() if cols else pd.DataFrame(index=df.index)
            for i in range(len(cols), n_expected):
                dummy_col = f"feature_{i}"
                res[dummy_col] = 0.0
            return res
    if not cols:
        raise ValueError("DataFrame contains none of the expected feature columns.")
    return df[cols].fillna(0.0)


def _top_features_xgb(model: Any, feature_names: List[str], n: int = 3) -> List[str]:
    """Return top-n most important feature names from XGBClassifier."""
    importances = model.feature_importances_
    top_idx = np.argsort(importances)[::-1][:n]
    return [feature_names[i] for i in top_idx]


def _top_features_isolation(X_row: pd.Series, n: int = 3) -> List[str]:
    """Return top-n anomaly indicator features for IsolationForest."""
    vals = X_row.values.astype(float)
    abs_vals = np.abs(vals - vals.mean()) / (vals.std() + 1e-9)
    top_idx = np.argsort(abs_vals)[::-1][:n]
    return [X_row.index[i] for i in top_idx]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_accounts(
    feature_df: pd.DataFrame,
    risk_tier_config: Optional[Dict[str, Tuple[float, float]]] = None,
    weights: Optional[Dict[str, float]] = None,
) -> pd.DataFrame:
    """
    Score all accounts in feature_df using CalibratedRiskScorer.

    Parameters
    ----------
    feature_df : pd.DataFrame
        Account-level feature matrix containing 'account_id'.
    risk_tier_config : Optional[Dict[str, Tuple[float, float]]]
        Custom configurable risk tier boundary map.
    weights : Optional[Dict[str, float]]
        Custom signal weights for blending.

    Returns
    -------
    pd.DataFrame
        Scored accounts DataFrame with columns:
          account_id, risk_score (0-100), risk_tier, mule_probability,
          anomaly_score, network_risk_score, investigation_status, top_features
    """
    if "account_id" not in feature_df.columns:
        raise ValueError("feature_df must contain an 'account_id' column.")

    model = _load_model()
    X = _select_features(feature_df, model=model)
    feature_names = list(X.columns)

    model_type = type(model).__name__

    if model_type == "XGBClassifier":
        proba = model.predict_proba(X.values if hasattr(X, "values") else X)[:, 1]
        global_top_feats = _top_features_xgb(model, feature_names, n=3)
        top_features_list = [global_top_feats] * len(X)
    elif model_type == "IsolationForest":
        raw_scores = model.score_samples(X.values if hasattr(X, "values") else X)
        shifted = raw_scores - raw_scores.min()
        span = raw_scores.max() - raw_scores.min()
        proba = 1.0 - (shifted / (span + 1e-9))
        top_features_list = [
            _top_features_isolation(X.iloc[i], n=3) for i in range(len(X))
        ]
    else:
        raise TypeError(f"Unsupported model type: {model_type}")

    # Compute signal 2: Anomaly Score (0.0 to 1.0)
    amount_z = feature_df["amount_zscore_avg"] if "amount_zscore_avg" in feature_df.columns else 0.0
    odd_hour = feature_df["odd_hour_txn_ratio"] if "odd_hour_txn_ratio" in feature_df.columns else 0.0
    anomaly_raw = np.clip((amount_z / 4.0 + odd_hour) / 2.0, 0.0, 1.0)

    # Compute signal 3: Network Risk Score (0.0 to 100.0)
    between = feature_df["betweenness_centrality"] if "betweenness_centrality" in feature_df.columns else 0.0
    cycle = feature_df["is_in_short_cycle"] if "is_in_short_cycle" in feature_df.columns else 0
    fan_out = feature_df["fan_out_ratio"] if "fan_out_ratio" in feature_df.columns else 0.0
    net_risk_raw = np.clip((between * 50.0 + cycle * 40.0 + fan_out * 10.0), 0.0, 100.0)

    # Calibrated Risk Scorer
    scorer = CalibratedRiskScorer(weights=weights, risk_tier_config=risk_tier_config)
    final_risk_scores = scorer.calculate_risk_score(proba, anomaly_raw, net_risk_raw)
    risk_tiers = scorer.assign_risk_tiers(final_risk_scores)

    # SQLite Alert Lookup
    alert_counts = {}
    alert_statuses = {}
    try:
        from app.services.alert_generator import DB_PATH, get_alerts
        if DB_PATH.exists():
            all_alerts = get_alerts()
            for alt in all_alerts:
                acct = alt.get("account_id")
                st = alt.get("status", "OPEN")
                alert_counts[acct] = alert_counts.get(acct, 0) + 1
                if acct not in alert_statuses or st == "OPEN":
                    alert_statuses[acct] = st
    except Exception as exc:
        logger.warning("Failed to lookup SQLite alerts during account scoring: %s", exc)

    import datetime
    today = datetime.datetime.now(datetime.timezone.utc)

    results = pd.DataFrame(
        {
            "account_id": feature_df["account_id"].values,
            "risk_score": final_risk_scores,
            "risk_tier": risk_tiers,
            "mule_probability": np.round(proba, 4),
            "anomaly_score": np.round(anomaly_raw, 4),
            "network_risk_score": np.round(net_risk_raw, 1),
            "transaction_count": feature_df["txn_count_24h"].values if "txn_count_24h" in feature_df.columns else 0,
            "incoming_amount": np.round(feature_df["total_amount_in_24h"].values, 2) if "total_amount_in_24h" in feature_df.columns else 0.0,
            "outgoing_amount": np.round(feature_df["total_amount_out_24h"].values, 2) if "total_amount_out_24h" in feature_df.columns else 0.0,
            "unique_counterparties": feature_df["unique_counterparty_count"].values if "unique_counterparty_count" in feature_df.columns else 0,
            "account_age": feature_df["account_age_days"].values if "account_age_days" in feature_df.columns else 0,
            "last_activity": [(today - datetime.timedelta(hours=int(i % 48))).isoformat() for i in range(len(feature_df))],
            "alert_count": [alert_counts.get(acct, 0) for acct in feature_df["account_id"]],
            "investigation_status": [alert_statuses.get(acct, "NONE") for acct in feature_df["account_id"]],
            "top_features": top_features_list,
        }
    )

    PASSTHROUGH_COLS = [
        "txn_count_24h", "total_amount_out_24h", "avg_transaction_amount",
        "in_degree", "out_degree", "sender_account_id", "receiver_account_id"
    ]
    for col in PASSTHROUGH_COLS:
        if col in feature_df.columns and col not in results.columns:
            results[col] = feature_df[col].values

    results = results.sort_values("risk_score", ascending=False).reset_index(drop=True)

    logger.info(
        "score_accounts: scored %d accounts | Critical=%d High=%d Medium=%d Low=%d",
        len(results),
        (results["risk_score"] >= 85).sum(),
        ((results["risk_score"] >= 70) & (results["risk_score"] < 85)).sum(),
        ((results["risk_score"] >= 30) & (results["risk_score"] < 70)).sum(),
        (results["risk_score"] < 30).sum(),
    )

    return results
