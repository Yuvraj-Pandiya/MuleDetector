"""
app/services/risk_scorer.py
============================
Score a DataFrame of accounts against the persisted mule-detection model.

Public API
----------
score_accounts(feature_df) -> pd.DataFrame
    Returns a DataFrame with columns:
        account_id | risk_score | risk_tier | top_features

    risk_tier thresholds:
        Low    < 0.30
        Medium 0.30 – 0.70
        High   > 0.70

    top_features: list of the 3 feature names most responsible for the
    score (derived from the model's feature importances for XGBoost, or
    absolute anomaly scores for IsolationForest).
"""

from __future__ import annotations

import logging
import pathlib
from typing import Any

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths — kept in sync with model_trainer.py
# ---------------------------------------------------------------------------
_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
MODEL_PATH = _DATA_DIR / "model.pkl"

# ---------------------------------------------------------------------------
# Risk tier thresholds
# ---------------------------------------------------------------------------
TIER_HIGH_THRESHOLD = 0.70
TIER_LOW_THRESHOLD = 0.30

# Feature columns consumed by the model (same order as training)
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
# Internal helpers
# ---------------------------------------------------------------------------

def _load_model() -> Any:
    """Load the persisted model from disk; auto-train default model if absent."""
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


def _select_features(df: pd.DataFrame) -> pd.DataFrame:
    """Select and order only the expected feature columns present in df."""
    cols = [c for c in FEATURE_SCHEMA_COLUMNS if c in df.columns]
    if not cols:
        raise ValueError("DataFrame contains none of the expected feature columns.")
    return df[cols]


def _tier(score: float) -> str:
    if score > TIER_HIGH_THRESHOLD:
        return "High"
    if score >= TIER_LOW_THRESHOLD:
        return "Medium"
    return "Low"


def _top_features_xgb(model: Any, feature_names: list[str], n: int = 3) -> list[str]:
    """Return the n most-important feature names from an XGBClassifier."""
    importances = model.feature_importances_  # shape (n_features,)
    top_idx = np.argsort(importances)[::-1][:n]
    return [feature_names[i] for i in top_idx]


def _top_features_isolation(X_row: pd.Series, n: int = 3) -> list[str]:
    """
    IsolationForest has no .feature_importances_.
    Use the absolute magnitude of each feature value (z-scored within the
    row's own feature set) as a rough proxy for which features are most
    unusual.  Not SHAP — just a lightweight fallback signal.
    """
    vals = X_row.values.astype(float)
    abs_vals = np.abs(vals - vals.mean()) / (vals.std() + 1e-9)
    top_idx = np.argsort(abs_vals)[::-1][:n]
    return [X_row.index[i] for i in top_idx]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_accounts(feature_df: pd.DataFrame) -> pd.DataFrame:
    """Score all accounts in feature_df and return a results DataFrame.

    Parameters
    ----------
    feature_df:
        DataFrame conforming to docs/feature_schema.md.
        Must contain 'account_id'.

    Returns
    -------
    pd.DataFrame
        Columns: account_id, risk_score, risk_tier, top_features
        Sorted by risk_score descending.
    """
    if "account_id" not in feature_df.columns:
        raise ValueError("feature_df must contain an 'account_id' column.")

    model = _load_model()
    X = _select_features(feature_df)
    feature_names = list(X.columns)

    model_type = type(model).__name__

    if model_type == "XGBClassifier":
        # predict_proba returns [P(0), P(1)] — take the mule probability
        proba = model.predict_proba(X)[:, 1]
        global_top_feats = _top_features_xgb(model, feature_names, n=3)
        # Same top features for all rows (global importance-based, fast)
        top_features_list = [global_top_feats] * len(X)

    elif model_type == "IsolationForest":
        # score_samples: lower (more negative) = more anomalous
        raw_scores = model.score_samples(X)            # range ~ [-0.5, 0]
        # Normalise to [0, 1] so "High" = most anomalous
        shifted = raw_scores - raw_scores.min()
        span = raw_scores.max() - raw_scores.min()
        proba = 1.0 - (shifted / (span + 1e-9))       # invert so anomalous → high
        top_features_list = [
            _top_features_isolation(X.iloc[i], n=3) for i in range(len(X))
        ]

    else:
        raise TypeError(f"Unsupported model type: {model_type}")

    results = pd.DataFrame(
        {
            "account_id": feature_df["account_id"].values,
            "risk_score": np.round(proba, 4),
            "risk_tier": [_tier(s) for s in proba],
            "top_features": top_features_list,
        }
    )

    # Attach raw feature columns so the frontend can display Txn Count, Volume, Fan In/Out
    PASSTHROUGH_COLS = [
        "txn_count_24h", "total_amount_out_24h", "avg_transaction_amount",
        "in_degree", "out_degree",
    ]
    for col in PASSTHROUGH_COLS:
        if col in feature_df.columns:
            results[col] = feature_df[col].values

    # Sort by risk_score descending — criterion 1
    results = results.sort_values("risk_score", ascending=False).reset_index(drop=True)

    logger.info(
        "score_accounts: scored %d accounts  High=%d  Medium=%d  Low=%d",
        len(results),
        (results["risk_tier"] == "High").sum(),
        (results["risk_tier"] == "Medium").sum(),
        (results["risk_tier"] == "Low").sum(),
    )

    return results
