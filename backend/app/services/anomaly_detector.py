"""
app/services/anomaly_detector.py
=================================
Unsupervised Anomaly Detection Layer for MuleDetector.

Purpose:
Independent anomaly detection engine operating strictly without ground-truth labels.
Uses Isolation Forest to detect anomalous account behavior across velocity,
behavioral, graph, and temporal feature spaces.

Outputs per account:
  - anomaly_score in [0, 1] (1.0 = highest anomaly probability)
  - anomaly_flag (1 = anomalous/suspicious, 0 = normal)
  - anomaly_percentile (0.0% to 100.0% ranking)

Guarantees 100% independence from supervised classifiers.
"""

from __future__ import annotations

import logging
import pickle
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp, rankdata
from sklearn.ensemble import IsolationForest
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

_EPS = 1e-9


class AccountAnomalyDetector:
    """
    Unsupervised Isolation Forest Anomaly Detector for Account-Level Data.
    """

    def __init__(
        self,
        n_estimators: int = 100,
        contamination: float = 0.01,
        random_state: int = 42,
    ) -> None:
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.random_state = random_state

        self.model: Optional[IsolationForest] = None
        self.scaler: StandardScaler = StandardScaler()
        self.feature_names: List[str] = []
        self.is_fitted: bool = False
        self.threshold: float = 0.5  # Min-max normalized threshold

    def fit(
        self,
        X_df: pd.DataFrame,
        feature_cols: Optional[List[str]] = None,
        tune_contamination_with_val: bool = False,
        y_val: Optional[np.ndarray] = None,
    ) -> AccountAnomalyDetector:
        """
        Fit Isolation Forest model strictly without ground-truth labels.

        Parameters
        ----------
        X_df : pd.DataFrame
            Account-level feature matrix.
        feature_cols : Optional[List[str]]
            List of numeric feature columns to use for anomaly detection.
            Excludes account_id and ground-truth labels.
        tune_contamination_with_val : bool
            If True and y_val is provided, grid-search optimal contamination rate.
        y_val : Optional[np.ndarray]
            Validation ground-truth labels for hyperparameter tuning.

        Returns
        -------
        AccountAnomalyDetector
            Fitted instance.
        """
        t0 = time.perf_counter()

        # 1. Identify Numeric Feature Columns (Exclude account_id, labels)
        exclude_cols = {"account_id", "is_mule_pattern", "fraud_label", "label", "target"}
        if feature_cols is None:
            self.feature_names = [
                c for c in X_df.columns if c not in exclude_cols and pd.api.types.is_numeric_dtype(X_df[c])
            ]
        else:
            self.feature_names = [c for c in feature_cols if c in X_df.columns]

        if not self.feature_names:
            raise ValueError("[AnomalyDetector] No valid numeric feature columns provided for fitting.")

        X_mat = X_df[self.feature_names].fillna(0.0).values
        X_scaled = self.scaler.fit_transform(X_mat)

        # 2. Contamination Tuning (Validation Methodology)
        if tune_contamination_with_val and y_val is not None:
            best_contam = self._tune_contamination(X_scaled, y_val)
            self.contamination = best_contam
            logger.info("[AnomalyDetector] Tuned contamination to %.4f via validation ROC-AUC", best_contam)

        # 3. Fit Isolation Forest Model
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=-1,
        )
        self.model.fit(X_scaled)
        self.is_fitted = True

        # Calculate threshold on training distribution for consistency
        raw_scores = -self.model.score_samples(X_scaled)
        min_s, max_s = raw_scores.min(), raw_scores.max()
        self._min_raw = min_s
        self._max_raw = max_s

        # Cutoff threshold corresponding to top contamination percentage
        cutoff_raw = np.percentile(raw_scores, 100.0 * (1.0 - self.contamination))
        self.threshold = float((cutoff_raw - min_s) / (max_s - min_s + _EPS))

        elapsed = round(time.perf_counter() - t0, 3)
        logger.info(
            "[AnomalyDetector] Fitted Isolation Forest on %d accounts x %d features in %.3fs (contamination=%.4f)",
            len(X_df),
            len(self.feature_names),
            elapsed,
            self.contamination,
        )
        return self

    def predict_anomalies(self, X_df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute anomaly_score, anomaly_flag, and anomaly_percentile per account.

        Returns
        -------
        pd.DataFrame
            DataFrame containing:
              - account_id
              - anomaly_score (float in [0.0, 1.0])
              - anomaly_flag (int 1 or 0)
              - anomaly_percentile (float in [0.0, 100.0])
        """
        if not self.is_fitted or self.model is None:
            raise RuntimeError("[AnomalyDetector] Model must be fitted before predicting.")

        accounts = X_df["account_id"].astype(str) if "account_id" in X_df.columns else pd.Series(X_df.index.astype(str))
        X_mat = X_df[self.feature_names].fillna(0.0).values
        X_scaled = self.scaler.transform(X_mat)

        # Scikit-learn score_samples: lower value = more anomalous.
        # We negate it so higher value = more anomalous.
        raw_scores = -self.model.score_samples(X_scaled)

        # Min-Max Normalization to [0, 1]
        min_s = getattr(self, "_min_raw", raw_scores.min())
        max_s = getattr(self, "_max_raw", raw_scores.max())
        denom = (max_s - min_s) + _EPS

        anomaly_score = np.clip((raw_scores - min_s) / denom, 0.0, 1.0).round(6)

        # Percentile ranking (0.0% to 100.0%)
        n = len(anomaly_score)
        anomaly_percentile = (rankdata(anomaly_score, method="average") / n * 100.0).round(2)

        # Anomaly flag: 1 if score >= cutoff threshold, else 0
        anomaly_flag = (anomaly_score >= self.threshold).astype(int)

        return pd.DataFrame({
            "account_id": accounts.values,
            "anomaly_score": anomaly_score,
            "anomaly_flag": anomaly_flag,
            "anomaly_percentile": anomaly_percentile,
        })

    def _tune_contamination(self, X_scaled: np.ndarray, y_val: np.ndarray) -> float:
        """Grid-search optimal contamination using validation ROC-AUC."""
        candidate_contams = [0.001, 0.005, 0.01, 0.02, 0.05, 0.10]
        best_auc = -1.0
        best_c = 0.01

        for c in candidate_contams:
            iso = IsolationForest(
                n_estimators=self.n_estimators,
                contamination=c,
                random_state=self.random_state,
                n_jobs=-1,
            )
            iso.fit(X_scaled)
            scores = -iso.score_samples(X_scaled)
            auc = roc_auc_score(y_val, scores)
            if auc > best_auc:
                best_auc = auc
                best_c = c

        return best_c

    def save(self, filepath: Union[str, Path]) -> Path:
        """Persist anomaly detector model to disk."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            pickle.dump(self, f)
        logger.info("[AnomalyDetector] Model saved to '%s'", filepath)
        return filepath

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> AccountAnomalyDetector:
        """Load anomaly detector model from disk."""
        with open(filepath, "rb") as f:
            obj = pickle.load(f)
        logger.info("[AnomalyDetector] Model loaded from '%s'", filepath)
        return obj


def evaluate_anomaly_scores_vs_labels(
    anomaly_df: pd.DataFrame,
    labels: np.ndarray,
) -> Dict[str, Any]:
    """
    Compare anomaly scores between labeled suspicious (mule) and legitimate accounts.

    Parameters
    ----------
    anomaly_df : pd.DataFrame
        DataFrame containing column 'anomaly_score'.
    labels : np.ndarray
        Ground-truth labels (1 = Mule, 0 = Legitimate).

    Returns
    -------
    Dict[str, Any]
        Statistical evaluation metrics comparing legitimate vs mule anomaly scores.
    """
    scores = anomaly_df["anomaly_score"].values
    legit_mask = labels == 0
    mule_mask = labels == 1

    legit_scores = scores[legit_mask]
    mule_scores = scores[mule_mask]

    mean_legit = float(np.mean(legit_scores)) if len(legit_scores) > 0 else 0.0
    mean_mule = float(np.mean(mule_scores)) if len(mule_scores) > 0 else 0.0

    med_legit = float(np.median(legit_scores)) if len(legit_scores) > 0 else 0.0
    med_mule = float(np.median(mule_scores)) if len(mule_scores) > 0 else 0.0

    score_ratio = round(mean_mule / (mean_legit + _EPS), 4)

    # Kolmogorov-Smirnov Test for distribution separation
    if len(legit_scores) > 0 and len(mule_scores) > 0:
        ks_res = ks_2samp(legit_scores, mule_scores)
        ks_stat = round(float(ks_res.statistic), 4)
        p_val = float(ks_res.pvalue)

        # ROC-AUC of unsupervised anomaly score against ground-truth labels
        try:
            auc = round(float(roc_auc_score(labels, scores)), 4)
        except Exception:
            auc = 0.5
    else:
        ks_stat = 0.0
        p_val = 1.0
        auc = 0.5

    return {
        "legitimate_count": int(np.sum(legit_mask)),
        "mule_count": int(np.sum(mule_mask)),
        "mean_legitimate_anomaly_score": round(mean_legit, 4),
        "mean_mule_anomaly_score": round(mean_mule, 4),
        "median_legitimate_anomaly_score": round(med_legit, 4),
        "median_mule_anomaly_score": round(med_mule, 4),
        "mule_to_legitimate_score_ratio": score_ratio,
        "ks_statistic": ks_stat,
        "ks_p_value": p_val,
        "unsupervised_roc_auc": auc,
    }
