"""
app/services/model_trainer.py
==============================
Core training logic for the MuleDetector ML pipeline.

Public API
----------
train_model(feature_df, label_col='is_mule_pattern') -> dict
    Trains a supervised XGBoost classifier (or falls back to IsolationForest
    when the label column is absent or single-class), then persists:
      - app/data/model.pkl    (joblib)
      - app/data/metrics.json (JSON)
    Returns the metrics dict.
"""

from __future__ import annotations

import json
import logging
import pathlib
import time
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
MODEL_PATH = _DATA_DIR / "model.pkl"
METRICS_PATH = _DATA_DIR / "metrics.json"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
RANDOM_SEED = 42
TEST_SIZE = 0.20
FEATURE_SCHEMA_COLUMNS: list[str] = [
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _select_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return only the known feature columns that are present in df."""
    cols = [c for c in FEATURE_SCHEMA_COLUMNS if c in df.columns]
    if not cols:
        raise ValueError("DataFrame contains none of the expected feature columns.")
    return df[cols]


def _is_supervised(df: pd.DataFrame, label_col: str) -> bool:
    """Return True only when label_col exists and has both classes."""
    if label_col not in df.columns:
        logger.warning("Label column '%s' not found — falling back to IsolationForest.", label_col)
        return False
    unique = df[label_col].dropna().unique()
    if len(unique) < 2:
        logger.warning(
            "Label column '%s' has only one class (%s) — falling back to IsolationForest.",
            label_col,
            unique,
        )
        return False
    return True


# ---------------------------------------------------------------------------
# Supervised path — XGBoost
# ---------------------------------------------------------------------------

def _train_supervised(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
) -> tuple[Any, dict]:
    """Train XGBoost with scale_pos_weight for class imbalance, return (model, metrics)."""

    n_neg = int((y_train == 0).sum())
    n_pos = int((y_train == 1).sum())
    scale_pos_weight = n_neg / max(n_pos, 1)

    logger.info(
        "XGBoost: train=%d  (pos=%d, neg=%d)  scale_pos_weight=%.2f",
        len(y_train), n_pos, n_neg, scale_pos_weight,
    )

    model = XGBClassifier(
        n_estimators=150,        # fewer trees → less memorisation
        max_depth=4,             # shallower → less overfit (was 6)
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.7,    # use 70% of features per tree
        min_child_weight=5,      # need ≥5 samples per leaf → prevents tiny splits
        reg_lambda=2.0,          # L2 weight regularisation
        reg_alpha=0.1,           # L1 sparsity regularisation
        max_delta_step=1,        # helps with extreme class imbalance stability
        scale_pos_weight=scale_pos_weight,
        random_state=RANDOM_SEED,
        eval_metric="logloss",
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    cm = confusion_matrix(y_test, y_pred).tolist()

    metrics: dict = {
        "unsupervised": False,
        "model_type": "XGBClassifier",
        "train_rows": len(y_train),
        "test_rows": len(y_test),
        "positive_rate_train": round(float(y_train.mean()), 4),
        "scale_pos_weight": round(scale_pos_weight, 4),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, y_prob)), 4),
        "confusion_matrix": cm,
        "feature_columns": list(X_train.columns),
    }

    return model, metrics


# ---------------------------------------------------------------------------
# Fallback path — IsolationForest
# ---------------------------------------------------------------------------

def _train_unsupervised(X_train: pd.DataFrame, X_test: pd.DataFrame) -> tuple[Any, dict]:
    """Train IsolationForest; return (model, metrics). No label-dependent metrics."""

    logger.info("IsolationForest: train=%d  test=%d", len(X_train), len(X_test))

    model = IsolationForest(
        n_estimators=200,
        contamination=0.05,  # expected mule rate ~5%
        random_state=RANDOM_SEED,
    )
    model.fit(X_train)

    # IsolationForest predict: -1 = anomaly (mule), 1 = normal
    raw_preds = model.predict(X_test)
    anomaly_count = int((raw_preds == -1).sum())

    metrics: dict = {
        "unsupervised": True,
        "model_type": "IsolationForest",
        "train_rows": len(X_train),
        "test_rows": len(X_test),
        "anomaly_count_test": anomaly_count,
        "anomaly_rate_test": round(anomaly_count / max(len(X_test), 1), 4),
        "feature_columns": list(X_train.columns),
    }

    return model, metrics


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def train_model(
    feature_df: pd.DataFrame,
    label_col: str = "is_mule_pattern",
) -> dict:
    """Train a mule-detection model and persist artefacts.

    Parameters
    ----------
    feature_df:
        DataFrame conforming to docs/feature_schema.md.  May or may not
        contain the label column.
    label_col:
        Name of the binary target column.

    Returns
    -------
    dict
        Metrics written to app/data/metrics.json.
    """
    t0 = time.perf_counter()

    _DATA_DIR.mkdir(parents=True, exist_ok=True)

    X = _select_features(feature_df)

    supervised = _is_supervised(feature_df, label_col)

    if supervised:
        y = feature_df[label_col].astype(int)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=TEST_SIZE,
            random_state=RANDOM_SEED,
            stratify=y,
        )
        model, metrics = _train_supervised(X_train, X_test, y_train, y_test)
    else:
        X_train, X_test = train_test_split(
            X,
            test_size=TEST_SIZE,
            random_state=RANDOM_SEED,
        )
        model, metrics = _train_unsupervised(X_train, X_test)

    elapsed = round(time.perf_counter() - t0, 3)
    metrics["training_time_seconds"] = elapsed

    # --- persist model ---
    joblib.dump(model, MODEL_PATH)
    logger.info("Model saved → %s", MODEL_PATH)

    # --- persist metrics ---
    with open(METRICS_PATH, "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)
    logger.info("Metrics saved → %s", METRICS_PATH)

    return metrics
