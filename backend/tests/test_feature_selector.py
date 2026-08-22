"""
tests/test_feature_selector.py
================================
Unit tests for the FeatureSelector pipeline.

Tests
-----
1. test_missingness_scoring             -- high-missing features correctly flagged
2. test_mutual_information_scores_positive -- MI >= 0 for all features
3. test_mannwhitney_pvalue_range        -- p-values in [0, 1]
4. test_xgboost_importance_sums_to_one -- gain importances sum to ~1.0
5. test_shap_importance_nonnegative    -- SHAP global values >= 0
6. test_retention_ignores_low_correlation -- near-zero correlation alone NEVER causes rejection
"""

from __future__ import annotations

import pathlib
import tempfile

import numpy as np
import pandas as pd
import pytest

from app.services.feature_selector import FeatureSelector, _feature_group


# ---------------------------------------------------------------------------
# Shared fixture: small synthetic feature DataFrame with known mule labels
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def synthetic_df() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    n_legit = 200
    n_mule  = 20

    legit = {
        "txn_count_1h":               rng.integers(0, 5, n_legit),
        "txn_count_24h":              rng.integers(1, 30, n_legit),
        "total_amount_out_24h":       rng.uniform(50, 5000, n_legit),
        "avg_transaction_amount":     rng.uniform(20, 500, n_legit),
        "ratio_received_to_sent_24h": rng.uniform(0.1, 2.0, n_legit),
        "account_age_days":           rng.integers(100, 3650, n_legit),
        "is_new_high_volume_flag":    rng.integers(0, 2, n_legit),
        "in_degree":                  rng.integers(1, 10, n_legit),
        "out_degree":                 rng.integers(1, 10, n_legit),
        "betweenness_centrality":     rng.uniform(0, 0.10, n_legit),
        "amount_zscore_avg":          rng.normal(0, 0.5, n_legit),
        "is_mule_pattern":            np.zeros(n_legit, dtype=int),
    }
    mule = {
        "txn_count_1h":               rng.integers(5, 20, n_mule),
        "txn_count_24h":              rng.integers(20, 80, n_mule),
        "total_amount_out_24h":       rng.uniform(2000, 15000, n_mule),
        "avg_transaction_amount":     rng.uniform(500, 3000, n_mule),
        "ratio_received_to_sent_24h": rng.uniform(1.5, 5.0, n_mule),
        "account_age_days":           rng.integers(1, 60, n_mule),
        "is_new_high_volume_flag":    rng.integers(0, 2, n_mule),
        "in_degree":                  rng.integers(5, 25, n_mule),
        "out_degree":                 rng.integers(10, 40, n_mule),
        "betweenness_centrality":     rng.uniform(0.05, 0.30, n_mule),
        "amount_zscore_avg":          rng.normal(1.5, 0.5, n_mule),
        "is_mule_pattern":            np.ones(n_mule, dtype=int),
    }
    frames = [
        pd.DataFrame({k: v for k, v in legit.items()}),
        pd.DataFrame({k: v for k, v in mule.items()}),
    ]
    df = pd.concat(frames, ignore_index=True)
    df.insert(0, "account_id", [f"ACC{i:06d}" for i in range(len(df))])
    return df.sample(frac=1, random_state=99).reset_index(drop=True)


@pytest.fixture(scope="module")
def selector_with_results(synthetic_df, tmp_path_factory):
    """Run FeatureSelector once and return (selector, summary, ranking_df)."""
    data_dir = tmp_path_factory.mktemp("data")
    sel = FeatureSelector(data_dir=data_dir)
    summary = sel.run(synthetic_df, label_col="is_mule_pattern")
    return sel, summary, sel._ranking_df


# ---------------------------------------------------------------------------
# Test 1: Missingness scoring
# ---------------------------------------------------------------------------
def test_missingness_scoring():
    """Features with >30% missing values should be correctly measured."""
    sel = FeatureSelector.__new__(FeatureSelector)

    df_with_missing = pd.DataFrame({
        "feat_good":  [1.0] * 100,
        "feat_50pct": [None if i % 2 == 0 else 1.0 for i in range(100)],
        "feat_all":   [None] * 100,
    })
    scores = sel._score_missingness(df_with_missing)

    assert scores["feat_good"] == pytest.approx(0.0, abs=1e-6),         "feat_good should have 0% missingness"
    assert scores["feat_50pct"] == pytest.approx(0.50, abs=0.01),         "feat_50pct should have ~50% missingness"
    assert scores["feat_all"] == pytest.approx(1.0, abs=1e-6),         "feat_all should have 100% missingness"


# ---------------------------------------------------------------------------
# Test 2: Mutual Information >= 0
# ---------------------------------------------------------------------------
def test_mutual_information_scores_positive(selector_with_results, synthetic_df):
    """All mutual information scores must be non-negative."""
    sel, _, ranking_df = selector_with_results
    X = synthetic_df[[c for c in synthetic_df.columns
                       if c not in ("account_id", "is_mule_pattern")
                       and pd.api.types.is_numeric_dtype(synthetic_df[c])]].copy()
    y = synthetic_df["is_mule_pattern"].values
    mi_scores = sel._score_mutual_information(X, y)
    for feat, val in mi_scores.items():
        assert val >= 0.0, f"MI score for {feat} should be >= 0, got {val}"


# ---------------------------------------------------------------------------
# Test 3: Mann-Whitney p-values in [0, 1]
# ---------------------------------------------------------------------------
def test_mannwhitney_pvalue_range(selector_with_results, synthetic_df):
    """All Mann-Whitney p-values must be in [0, 1]."""
    sel, _, ranking_df = selector_with_results
    X = synthetic_df[[c for c in synthetic_df.columns
                       if c not in ("account_id", "is_mule_pattern")
                       and pd.api.types.is_numeric_dtype(synthetic_df[c])]].copy()
    y = synthetic_df["is_mule_pattern"].values
    mw_scores = sel._score_univariate(X, y)
    for feat, d in mw_scores.items():
        pval = d["pvalue"]
        eff  = d["effect_size"]
        assert 0.0 <= pval <= 1.0, f"p-value for {feat} out of range: {pval}"
        assert 0.0 <= eff  <= 1.0, f"effect size for {feat} out of range: {eff}"


# ---------------------------------------------------------------------------
# Test 4: XGBoost importances sum to ~1.0
# ---------------------------------------------------------------------------
def test_xgboost_importance_sums_to_one(selector_with_results, synthetic_df):
    """XGBoost gain-based importances should sum to approximately 1.0."""
    sel, _, ranking_df = selector_with_results
    X = synthetic_df[[c for c in synthetic_df.columns
                       if c not in ("account_id", "is_mule_pattern")
                       and pd.api.types.is_numeric_dtype(synthetic_df[c])]].copy()
    y = synthetic_df["is_mule_pattern"].values
    xgb_scores, _ = sel._score_xgboost_importance(X, y)
    total = sum(xgb_scores.values())
    assert total == pytest.approx(1.0, abs=0.01),         f"XGBoost importances sum to {total}, expected ~1.0"


# ---------------------------------------------------------------------------
# Test 5: SHAP importances are non-negative
# ---------------------------------------------------------------------------
def test_shap_importance_nonnegative(selector_with_results, synthetic_df):
    """Global SHAP (mean |SHAP|) values must all be >= 0."""
    sel, _, _ = selector_with_results
    X = synthetic_df[[c for c in synthetic_df.columns
                       if c not in ("account_id", "is_mule_pattern")
                       and pd.api.types.is_numeric_dtype(synthetic_df[c])]].copy()
    y = synthetic_df["is_mule_pattern"].values
    xgb_scores, xgb_model = sel._score_xgboost_importance(X, y)
    shap_scores = sel._score_shap_importance(xgb_model, X)
    for feat, val in shap_scores.items():
        assert val >= 0.0, f"SHAP importance for {feat} should be >= 0, got {val}"


# ---------------------------------------------------------------------------
# Test 6: Low correlation alone NEVER causes rejection
# ---------------------------------------------------------------------------
def test_retention_ignores_low_correlation():
    """
    Core invariant: A feature with near-zero Pearson/Spearman but
    non-trivial MI or SHAP must be RETAINED.
    """
    sel = FeatureSelector.__new__(FeatureSelector)

    # Simulate a feature with near-zero linear correlation but high MI
    # (e.g., a purely nonlinear, high-importance feature)
    row_retained = pd.Series({
        "feature_name":            "some_nonlinear_feature",
        "feature_group":           "behavioral",
        "missingness_fraction":    0.00,   # no missing
        "pearson_corr":            0.001,  # near-zero linear correlation
        "spearman_corr":           0.002,  # near-zero rank correlation
        "mi_score":                0.350,  # strong nonlinear relationship
        "mannwhitney_pvalue":      0.001,
        "mannwhitney_effect_size": 0.45,
        "xgb_importance":          0.080,
        "shap_importance":         0.060,
        "composite_score":         0.420,  # high composite (MI + MW + XGB + SHAP)
        "mi_rank":                 2,
        "mannwhitney_rank":        3,
        "xgb_rank":                4,
        "shap_rank":               5,
        "interpretation":          "test",
        "method":                  "composite(MI+MW+XGB+SHAP)",
    })
    decision = sel._decide_retention(row_retained)
    assert decision == "RETAINED", (
        "A feature with low linear correlation but high MI/SHAP/XGB must be RETAINED. "
        f"Got: {decision}"
    )

    # Also verify: high missing + near-zero composite -> REJECTED
    row_rejected = row_retained.copy()
    row_rejected["missingness_fraction"] = 0.60   # high missing
    row_rejected["composite_score"]      = 0.01   # near-zero composite
    decision2 = sel._decide_retention(row_rejected)
    assert decision2 == "REJECTED", (
        "A feature with >30% missing AND near-zero composite score should be REJECTED. "
        f"Got: {decision2}"
    )
