"""
app/services/explainer.py
==========================
Explainability for the MuleDetector model.

Uses shap.TreeExplainer when the `shap` package is installed.
Falls back to XGBoost feature importances when shap is unavailable,
so the endpoint works even without the heavy shap/numba dependency.

Public API
----------
explain_account(account_id, feature_df) -> dict
    Returns:
        {
            "account_id": str,
            "risk_score": float,
            "risk_tier": str,
            "shap_available": bool,
            "top_shap_features": [
                {"feature": str, "shap_value": float, "feature_value": float},
                ...  # top 5
            ],
            "reason": str   # human-readable sentence
        }
"""

from __future__ import annotations

import logging
import pathlib
from typing import Any

import joblib
import numpy as np
import pandas as pd

# shap is an optional heavy dependency.  When unavailable the explainer
# falls back to XGBoost feature importances and marks shap_available=False.
try:
    import shap as _shap
    _SHAP_AVAILABLE = True
except Exception:  # ImportError or any init-time failure (e.g. missing numba)
    _shap = None  # type: ignore[assignment]
    _SHAP_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "shap not available — explainer will use feature-importance fallback. "
        "Install shap to enable SHAP-based explanations."
    )

from app.services.risk_scorer import (
    FEATURE_SCHEMA_COLUMNS,
    _select_features,
    _tier,
    score_accounts,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
MODEL_PATH = _DATA_DIR / "model.pkl"

# Human-readable templates keyed on direction of SHAP contribution
_POSITIVE_TEMPLATE = "elevated {feature} ({value:.4g}) pushes risk up"
_NEGATIVE_TEMPLATE = "low {feature} ({value:.4g}) suppresses risk"

# Feature → plain-English label for the reason string
_FEATURE_LABELS: dict[str, str] = {
    "txn_count_1h": "transactions in the last hour",
    "txn_count_24h": "transactions in the last 24 h",
    "txn_count_7d": "transactions in the last 7 days",
    "total_amount_out_24h": "total outbound amount (24 h)",
    "total_amount_in_24h": "total inbound amount (24 h)",
    "avg_transaction_amount": "average transaction amount",
    "max_transaction_amount": "maximum transaction amount",
    "ratio_received_to_sent_24h": "received-to-sent ratio",
    "avg_time_to_forward_funds_minutes": "average time to forward funds (minutes)",
    "unique_counterparty_count": "unique counterparty count",
    "account_age_days": "account age (days)",
    "is_new_high_volume_flag": "new high-volume account flag",
    "in_degree": "in-degree (transaction graph)",
    "out_degree": "out-degree (transaction graph)",
    "is_in_short_cycle": "participation in short transaction cycle",
    "betweenness_centrality": "betweenness centrality",
    "fan_in_ratio": "fan-in ratio",
    "fan_out_ratio": "fan-out ratio",
    "amount_zscore_avg": "amount Z-score",
    "round_number_txn_ratio": "round-number transaction ratio",
    "odd_hour_txn_ratio": "odd-hour transaction ratio",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_model() -> Any:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Trained model not found at '{MODEL_PATH}'. "
            "Call POST /train first."
        )
    return joblib.load(MODEL_PATH)


def _build_reason(top_features: list[dict]) -> str:
    """
    Compose a human-readable sentence from the top SHAP features.

    Example:
        "Risk driven by: elevated fan-out ratio (0.82) pushes risk up;
         low account age (45.0) pushes risk up; elevated odd-hour
         transaction ratio (0.61) pushes risk up."
    """
    parts: list[str] = []
    for item in top_features[:3]:  # use top 3 for the prose
        feature = item["feature"]
        value = item["feature_value"]
        shap_val = item["shap_value"]
        label = _FEATURE_LABELS.get(feature, feature.replace("_", " "))

        if shap_val >= 0:
            parts.append(f"elevated {label} ({value:.4g}) pushes risk up")
        else:
            parts.append(f"low {label} ({value:.4g}) suppresses risk")

    if not parts:
        return "No dominant features identified."

    joined = "; ".join(parts)
    return f"Risk driven by: {joined}."


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def explain_account(account_id: str, feature_df: pd.DataFrame) -> dict:
    """Explain the risk score for a single account using SHAP.

    Parameters
    ----------
    account_id:
        The account to explain — must exist in feature_df.
    feature_df:
        Full feature DataFrame (all accounts); must contain 'account_id'.

    Returns
    -------
    dict
        account_id, risk_score, risk_tier, top_shap_features (top 5),
        and a human-readable reason string.

    Raises
    ------
    KeyError
        If account_id is not found in feature_df.
    """
    # --- locate the row ---
    mask = feature_df["account_id"] == account_id
    if not mask.any():
        raise KeyError(f"account_id '{account_id}' not found in feature DataFrame.")

    row_df = feature_df[mask]
    X_row = _select_features(row_df)
    feature_names = list(X_row.columns)

    model = _load_model()
    model_type = type(model).__name__

    # --- compute feature attribution scores ---
    used_shap = False
    if _SHAP_AVAILABLE and model_type in ("XGBClassifier", "IsolationForest"):
        try:
            explainer = _shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_row)

            # Normalise across shap API versions:
            #   - shap <0.46: list of arrays [neg_class, pos_class]
            #   - shap 0.46+: single ndarray (1, n_features) for XGB
            sv_raw = np.array(shap_values)

            if model_type == "XGBClassifier":
                if sv_raw.ndim == 3:
                    sv = sv_raw[1, 0]   # old API class-1 slice
                elif sv_raw.ndim == 2:
                    sv = sv_raw[0]       # new API
                else:
                    sv = sv_raw.flatten()
            else:
                sv = sv_raw[0] if sv_raw.ndim == 2 else sv_raw.flatten()

            used_shap = True
            logger.debug("SHAP values computed for %s", account_id)

        except Exception as shap_exc:
            logger.warning(
                "TreeExplainer failed for %s (%s); using feature importances.",
                account_id, shap_exc,
            )

    if not used_shap:
        # Fallback: use model feature importances as proxy shap values
        if hasattr(model, "feature_importances_"):
            sv = model.feature_importances_
        else:
            sv = np.ones(len(feature_names))  # uniform fallback

    if model_type not in ("XGBClassifier", "IsolationForest"):
        raise TypeError(f"Unsupported model type: {model_type}")

    sv_arr = np.array(sv).flatten()

    # --- rank by absolute SHAP value, keep top 5 ---
    top_idx = np.argsort(np.abs(sv_arr))[::-1][:5]
    top_shap: list[dict] = []
    for i in top_idx:
        top_shap.append(
            {
                "feature": feature_names[i],
                "shap_value": round(float(sv_arr[i]), 6),
                "feature_value": round(float(X_row.iloc[0, i]), 4),
            }
        )

    # --- get the risk score from the scorer (single source of truth) ---
    scored_row = score_accounts(row_df)
    risk_score = float(scored_row.iloc[0]["risk_score"])
    risk_tier = scored_row.iloc[0]["risk_tier"]

    reason = _build_reason(top_shap)

    return {
        "account_id": account_id,
        "risk_score": round(risk_score, 4),
        "risk_tier": risk_tier,
        "shap_available": _SHAP_AVAILABLE and used_shap,
        "top_shap_features": top_shap,
        "reason": reason,
    }
