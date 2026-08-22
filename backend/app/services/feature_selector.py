"""
app/services/feature_selector.py
==================================
Comprehensive multi-method Feature Selection and Ranking Pipeline.

Evaluates all engineered features using 6 complementary methods:
  1. Missingness Audit          -- flags high-missing features
  2. Correlation Analysis       -- Pearson + Spearman vs label (informational only, NOT sole rejection criterion)
  3. Mutual Information         -- sklearn mutual_info_classif (captures nonlinear relationships)
  4. Univariate Statistical     -- Mann-Whitney U-test (non-parametric) + rank-biserial effect size
  5. XGBoost Feature Importance -- gain-based importance from trained classifier
  6. SHAP Global Importance     -- mean |SHAP value| per feature from TreeExplainer

Composite score = mean of min-max normalised scores from MI + Mann-Whitney effect size
                  + XGBoost gain + SHAP global importance.
Correlation is INFORMATIONAL ONLY and is NEVER the sole reason for rejection.

Core rejection policy:
  REJECTED only if missingness_fraction > 0.30 AND composite_score < 0.05.
  A feature with near-zero correlation but non-trivial MI or SHAP is always RETAINED.

Outputs to app/data/:
  - feature_ranking.csv
  - feature_importance_plot.png
  - top_10_features.json
  - top_20_features.json
  - feature_selection_report.json

Public API
----------
FeatureSelector(data_dir).run(feature_df, label_col) -> dict
run_feature_selection(feature_df, label_col, data_dir)  -> dict
"""

from __future__ import annotations

import json
import logging
import pathlib
import time
import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, pearsonr, spearmanr
from sklearn.ensemble import IsolationForest
from sklearn.feature_selection import mutual_info_classif
from xgboost import XGBClassifier

logger = logging.getLogger(__name__)

_EPS = 1e-12
MISSINGNESS_REJECT_THRESHOLD = 0.30
COMPOSITE_REJECT_THRESHOLD = 0.05

# ---------------------------------------------------------------------------
# Feature group taxonomy
# ---------------------------------------------------------------------------
_VELOCITY_FEATURES = {
    "txn_count_5min", "txn_count_15min", "txn_count_1h", "txn_count_6h",
    "txn_count_24h", "txn_count_7d", "amount_in_1h", "amount_out_1h",
    "amount_in_24h", "amount_out_24h", "amount_in_7d", "amount_out_7d",
    "total_amount_out_24h", "total_amount_in_24h", "max_transaction_amount",
    "average_transaction_amount", "avg_transaction_amount", "median_transaction_amount",
    "transaction_velocity_change", "recent_volume_vs_historical_volume",
}
_BEHAVIORAL_FEATURES = {
    "unique_sender_count", "unique_receiver_count", "unique_counterparty_count",
    "incoming_transaction_ratio", "outgoing_transaction_ratio",
    "ratio_received_to_sent_24h", "average_daily_transaction_count",
    "average_daily_amount", "active_days", "active_hours",
    "night_transaction_ratio", "weekend_transaction_ratio",
    "transaction_amount_std", "transaction_amount_cv", "account_age_days",
    "is_new_high_volume_flag", "new_account_high_volume_flag",
    "recent_vs_historical_transaction_ratio", "recent_vs_historical_amount_ratio",
    "avg_time_to_forward_funds_minutes",
}
_GRAPH_FEATURES = {
    "in_degree", "out_degree", "total_degree", "fan_in_ratio", "fan_out_ratio",
    "unique_in_counterparties", "unique_out_counterparties",
    "transaction_weighted_in_degree", "transaction_weighted_out_degree",
    "is_in_short_cycle", "short_cycle_indicator", "cycle_count",
    "pagerank", "betweenness_centrality", "clustering_coefficient",
}
_ANOMALY_FEATURES = {
    "amount_zscore_avg", "round_number_txn_ratio", "odd_hour_txn_ratio",
}

# ---------------------------------------------------------------------------
# Human-readable interpretations
# ---------------------------------------------------------------------------
_INTERPRETATIONS: Dict[str, str] = {
    "txn_count_1h": "High 1-hour burst count signals rapid pass-through mule activity",
    "txn_count_24h": "24-hour transaction frequency; mules operate at elevated daily cadence",
    "txn_count_7d": "7-day total activity; persistent high volume suggests automated mule behavior",
    "txn_count_5min": "Extreme 5-minute burst count signals scripted/bot mule operations",
    "txn_count_15min": "15-minute micro-burst; rapid layering indicator",
    "txn_count_6h": "6-hour window count; intermediate cadence for structured layering",
    "amount_in_1h": "Rapid inbound monetary spike; collection phase of mule cycle",
    "amount_out_1h": "Rapid outbound drain within 1h; forwarding phase of mule cycle",
    "amount_in_24h": "Total inbound volume; high inflows relative to history signal fund collection",
    "amount_out_24h": "Total outbound volume; fund forwarding metric",
    "amount_in_7d": "Weekly inbound flow total; sustained high inflow indicates persistent mule",
    "amount_out_7d": "Weekly outbound flow total",
    "total_amount_out_24h": "Alias for amount_out_24h -- 24h outbound monetary volume",
    "total_amount_in_24h": "Alias for amount_in_24h -- 24h inbound monetary volume",
    "max_transaction_amount": "Largest single transaction; unusually large transfers are a red flag",
    "average_transaction_amount": "Average amount; large avg with low variance signals structured transfers",
    "avg_transaction_amount": "Alias for average_transaction_amount",
    "median_transaction_amount": "Median amount; robust to outliers; very different from mean signals skew",
    "transaction_velocity_change": "1h count vs. 24h hourly baseline ratio; sudden acceleration is suspicious",
    "recent_volume_vs_historical_volume": "1h volume vs historical hourly volume; sudden surge is a mule signal",
    "unique_sender_count": "Number of distinct inbound senders; high count = fan-in collection hub",
    "unique_receiver_count": "Number of distinct outbound receivers; high count = layering/fan-out",
    "unique_counterparty_count": "Total network footprint; expansion signals active ring participation",
    "incoming_transaction_ratio": "Fraction of activity that is inbound; near-1.0 = pure collection node",
    "outgoing_transaction_ratio": "Fraction of activity that is outbound; near-1.0 = draining node",
    "ratio_received_to_sent_24h": "Inbound/outbound ratio in 24h; imbalanced ratios signal pass-through",
    "average_daily_transaction_count": "Daily frequency; high values on few active days signal burst activity",
    "average_daily_amount": "Daily monetary throughput; extreme values signal laundering bursts",
    "active_days": "Temporal spread; few active days with high volume = disposable mule account",
    "active_hours": "Hour diversity; 24-hour activity = bot/script mule indicator",
    "night_transaction_ratio": "Nocturnal (23:00-05:00) activity ratio; high ratio evades daytime monitoring",
    "weekend_transaction_ratio": "Weekend activity; high ratio exploits reduced compliance staffing",
    "transaction_amount_std": "Amount variance; near-zero std on large amounts = rigid structured transfers",
    "transaction_amount_cv": "Coefficient of variation (std/mean); extremely low CV signals automation",
    "account_age_days": "Account age; new accounts with high volume are classic disposable mules",
    "is_new_high_volume_flag": "Binary: new account (<30d) + high 7d volume; direct mule risk flag",
    "new_account_high_volume_flag": "Alias for is_new_high_volume_flag",
    "recent_vs_historical_transaction_ratio": "24h count vs historical daily avg; ratio >> 1 = suspicious surge",
    "recent_vs_historical_amount_ratio": "24h volume vs historical daily avg; ratio >> 1 = laundering burst",
    "avg_time_to_forward_funds_minutes": "Avg time to re-forward received funds; very short = rapid mule pass-through",
    "in_degree": "Network in-degree; high in-degree = collection hub (fan-in structure)",
    "out_degree": "Network out-degree; high out-degree = distribution hub (fan-out structure)",
    "total_degree": "Total graph connectivity; highly connected nodes are key mule ring nodes",
    "fan_in_ratio": "Fraction of connections that are inbound; near-1.0 = collector node",
    "fan_out_ratio": "Fraction of connections that are outbound; near-1.0 = forwarder node",
    "unique_in_counterparties": "Distinct inbound graph neighbors",
    "unique_out_counterparties": "Distinct outbound graph neighbors",
    "transaction_weighted_in_degree": "Monetary-weighted in-degree; large weight = high-value collection hub",
    "transaction_weighted_out_degree": "Monetary-weighted out-degree; large weight = high-value distribution node",
    "is_in_short_cycle": "Binary: participates in <=4-hop cycle; cyclic flows indicate circular laundering",
    "short_cycle_indicator": "Alias for is_in_short_cycle",
    "cycle_count": "Number of short cycles the account participates in; more = deeper ring involvement",
    "pagerank": "Network authority score; high PageRank = structurally important mule hub",
    "betweenness_centrality": "Bridge node score; high betweenness = intermediary mule bridging multiple rings",
    "clustering_coefficient": "Local cohesion; high clustering in dense subgraphs = ring membership",
    "amount_zscore_avg": "Z-score of account avg amount vs population; high z-score = outlier transaction sizes",
    "round_number_txn_ratio": "Fraction of round-number transactions (div by 100); high = structured smurfing",
    "odd_hour_txn_ratio": "Fraction of transactions 00:00-05:59; high = covert early-morning laundering",
}


def _feature_group(feat: str) -> str:
    if feat in _VELOCITY_FEATURES:
        return "velocity"
    if feat in _BEHAVIORAL_FEATURES:
        return "behavioral"
    if feat in _GRAPH_FEATURES:
        return "graph"
    if feat in _ANOMALY_FEATURES:
        return "anomaly"
    return "unknown"


class FeatureSelector:
    """Multi-method feature selection and ranking pipeline for MuleDetector."""

    def __init__(self, data_dir: Optional[pathlib.Path] = None) -> None:
        if data_dir is None:
            data_dir = pathlib.Path(__file__).parent.parent / "data"
        self.data_dir = pathlib.Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.ranking_csv_path = self.data_dir / "feature_ranking.csv"
        self.plot_path = self.data_dir / "feature_importance_plot.png"
        self.top10_path = self.data_dir / "top_10_features.json"
        self.top20_path = self.data_dir / "top_20_features.json"
        self.report_path = self.data_dir / "feature_selection_report.json"
        self._ranking_df: Optional[pd.DataFrame] = None
        self._xgb_model: Optional[XGBClassifier] = None
        self._feature_cols: List[str] = []

    # =========================================================================
    # Public entry point
    # =========================================================================

    def run(
        self,
        feature_df: pd.DataFrame,
        label_col: str = "is_mule_pattern",
    ) -> Dict[str, Any]:
        """Run the full 6-method feature selection and ranking pipeline."""
        t0 = time.perf_counter()
        logger.info("[FeatureSelector] Starting pipeline on %d rows", len(feature_df))

        exclude = {
            "account_id", label_col, "fraud_label", "label", "target",
            "anomaly_score", "anomaly_flag", "anomaly_percentile",
        }
        all_feature_cols = [
            c for c in feature_df.columns
            if c not in exclude and pd.api.types.is_numeric_dtype(feature_df[c])
        ]
        self._feature_cols = all_feature_cols
        X = feature_df[all_feature_cols].copy()
        logger.info("[FeatureSelector] Evaluating %d features", len(all_feature_cols))

        y, has_supervised_label = self._resolve_labels(feature_df, label_col, X)

        logger.info("[FeatureSelector] Method 1/6: Missingness audit")
        miss_scores = self._score_missingness(X)
        logger.info("[FeatureSelector] Method 2/6: Pearson + Spearman correlation")
        corr_scores = self._score_correlation(X, y)
        logger.info("[FeatureSelector] Method 3/6: Mutual information")
        mi_scores = self._score_mutual_information(X, y)
        logger.info("[FeatureSelector] Method 4/6: Mann-Whitney U univariate test")
        mw_scores = self._score_univariate(X, y)
        logger.info("[FeatureSelector] Method 5/6: XGBoost gain importance")
        xgb_scores, xgb_model = self._score_xgboost_importance(X, y)
        self._xgb_model = xgb_model
        logger.info("[FeatureSelector] Method 6/6: SHAP global importance")
        shap_scores = self._score_shap_importance(xgb_model, X)

        ranking_df = self._aggregate_ranks(
            all_feature_cols, miss_scores, corr_scores,
            mi_scores, mw_scores, xgb_scores, shap_scores,
        )
        self._ranking_df = ranking_df
        self._save_artifacts(ranking_df, xgb_model, X)

        elapsed = round(time.perf_counter() - t0, 3)
        logger.info("[FeatureSelector] Pipeline complete in %.3fs", elapsed)
        return self._build_summary(ranking_df, elapsed, has_supervised_label, len(all_feature_cols))

    # =========================================================================
    # Label Resolution
    # =========================================================================

    def _resolve_labels(
        self,
        feature_df: pd.DataFrame,
        label_col: str,
        X: pd.DataFrame,
    ) -> Tuple[np.ndarray, bool]:
        """Return (y_array, has_supervised_label). Falls back to IsolationForest proxy."""
        if label_col in feature_df.columns:
            unique_vals = feature_df[label_col].dropna().unique()
            if len(unique_vals) >= 2:
                y = feature_df[label_col].fillna(0).astype(int).values
                logger.info(
                    "[FeatureSelector] Supervised labels: %d positives / %d total",
                    int(y.sum()), len(y),
                )
                return y, True
        logger.warning(
            "[FeatureSelector] Label '%s' absent or single-class -- using IsolationForest proxy",
            label_col,
        )
        iso = IsolationForest(n_estimators=100, contamination=0.05, random_state=42, n_jobs=-1)
        X_filled = X.fillna(0.0)
        iso.fit(X_filled.values)
        raw_preds = iso.predict(X_filled.values)
        y = (raw_preds == -1).astype(int)
        logger.info("[FeatureSelector] Proxy labels: %d anomalies / %d total", int(y.sum()), len(y))
        return y, False

    # =========================================================================
    # Method 1: Missingness
    # =========================================================================

    def _score_missingness(self, X: pd.DataFrame) -> Dict[str, float]:
        """Return fraction of missing values per feature."""
        return X.isnull().mean().to_dict()

    # =========================================================================
    # Method 2: Correlation (informational only)
    # =========================================================================

    def _score_correlation(
        self,
        X: pd.DataFrame,
        y: np.ndarray,
    ) -> Dict[str, Dict[str, float]]:
        """
        Pearson and Spearman correlation with the label.
        INFORMATIONAL ONLY -- not part of composite score, never sole rejection criterion.
        A feature with near-zero correlation but non-trivial MI or SHAP is always RETAINED.
        """
        results: Dict[str, Dict[str, float]] = {}
        X_filled = X.fillna(0.0)
        for col in X_filled.columns:
            x_vals = X_filled[col].values.astype(float)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    pr, _ = pearsonr(x_vals, y)
                    sr, _ = spearmanr(x_vals, y)
                    pr = float(pr) if np.isfinite(pr) else 0.0
                    sr = float(sr) if np.isfinite(sr) else 0.0
                except Exception:
                    pr, sr = 0.0, 0.0
            results[col] = {"pearson": round(pr, 6), "spearman": round(sr, 6)}
        return results

    # =========================================================================
    # Method 3: Mutual Information
    # =========================================================================

    def _score_mutual_information(
        self,
        X: pd.DataFrame,
        y: np.ndarray,
    ) -> Dict[str, float]:
        """
        sklearn mutual_info_classif captures nonlinear feature-label dependencies
        that Pearson/Spearman correlation systematically miss.
        """
        X_filled = X.fillna(0.0).values
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mi_vals = mutual_info_classif(X_filled, y, random_state=42, n_neighbors=5)
        return {col: round(float(v), 8) for col, v in zip(X.columns, mi_vals)}

    # =========================================================================
    # Method 4: Mann-Whitney U
    # =========================================================================

    def _score_univariate(
        self,
        X: pd.DataFrame,
        y: np.ndarray,
    ) -> Dict[str, Dict[str, float]]:
        """
        Non-parametric Mann-Whitney U-test per feature.
        Effect size = rank-biserial correlation (absolute value in [0, 1]).
        Effect size is used in composite score; p-value is for audit/reporting.
        """
        results: Dict[str, Dict[str, float]] = {}
        X_filled = X.fillna(0.0)
        pos_mask = (y == 1)
        neg_mask = (y == 0)
        n_pos = int(pos_mask.sum())
        n_neg = int(neg_mask.sum())
        for col in X_filled.columns:
            x_vals = X_filled[col].values.astype(float)
            grp_pos = x_vals[pos_mask]
            grp_neg = x_vals[neg_mask]
            if len(grp_pos) == 0 or len(grp_neg) == 0:
                results[col] = {"pvalue": 1.0, "effect_size": 0.0}
                continue
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    stat, pval = mannwhitneyu(grp_pos, grp_neg, alternative="two-sided")
                r_rb = abs(1.0 - (2.0 * float(stat)) / (n_pos * n_neg + _EPS))
                r_rb = float(np.clip(r_rb, 0.0, 1.0))
                pval = float(pval)
            except Exception:
                pval, r_rb = 1.0, 0.0
            results[col] = {"pvalue": round(pval, 8), "effect_size": round(r_rb, 6)}
        return results

    # =========================================================================
    # Method 5: XGBoost Gain Importance
    # =========================================================================

    def _score_xgboost_importance(
        self,
        X: pd.DataFrame,
        y: np.ndarray,
    ) -> Tuple[Dict[str, float], XGBClassifier]:
        """Train XGBoost and extract normalised gain-based feature importances."""
        X_filled = X.fillna(0.0)
        n_pos = int(y.sum())
        n_neg = int((y == 0).sum())
        spw = max(float(n_neg) / max(n_pos, 1), 1.0)
        model = XGBClassifier(
            n_estimators=150, max_depth=4, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.7, min_child_weight=5,
            reg_lambda=2.0, reg_alpha=0.1, scale_pos_weight=spw,
            random_state=42, eval_metric="logloss", verbosity=0,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(X_filled.values, y)
        importances = model.feature_importances_
        return ({col: round(float(v), 8) for col, v in zip(X.columns, importances)}, model)

    # =========================================================================
    # Method 6: SHAP Global Importance
    # =========================================================================

    def _score_shap_importance(
        self,
        model: XGBClassifier,
        X: pd.DataFrame,
    ) -> Dict[str, float]:
        """Global SHAP importance = mean |SHAP| across all samples per feature."""
        try:
            import shap  # noqa: PLC0415
            X_filled = X.fillna(0.0)
            explainer = shap.TreeExplainer(model)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                shap_values = explainer.shap_values(X_filled.values)
            if isinstance(shap_values, list) and len(shap_values) == 2:
                sv = np.array(shap_values[1])
            else:
                sv = np.array(shap_values)
            mean_abs_shap = np.abs(sv).mean(axis=0)
            return {col: round(float(v), 8) for col, v in zip(X.columns, mean_abs_shap)}
        except Exception as exc:
            logger.warning("[FeatureSelector] SHAP failed (%s) -- using zeros", exc)
            return {col: 0.0 for col in X.columns}

    # =========================================================================
    # Composite Rank Aggregation
    # =========================================================================

    def _aggregate_ranks(
        self,
        feature_cols: List[str],
        miss_scores: Dict[str, float],
        corr_scores: Dict[str, Dict[str, float]],
        mi_scores: Dict[str, float],
        mw_scores: Dict[str, Dict[str, float]],
        xgb_scores: Dict[str, float],
        shap_scores: Dict[str, float],
    ) -> pd.DataFrame:
        """
        Composite score = mean of min-max normalised scores from:
          MI, Mann-Whitney effect size, XGBoost gain, SHAP global importance.
        Correlation is metadata only -- NOT in composite, NOT for rejection.
        """
        rows = []
        for feat in feature_cols:
            rows.append({
                "feature_name":            feat,
                "feature_group":           _feature_group(feat),
                "missingness_fraction":    round(miss_scores.get(feat, 0.0), 6),
                "pearson_corr":            corr_scores.get(feat, {}).get("pearson", 0.0),
                "spearman_corr":           corr_scores.get(feat, {}).get("spearman", 0.0),
                "mi_score":                mi_scores.get(feat, 0.0),
                "mannwhitney_pvalue":      mw_scores.get(feat, {}).get("pvalue", 1.0),
                "mannwhitney_effect_size": mw_scores.get(feat, {}).get("effect_size", 0.0),
                "xgb_importance":          xgb_scores.get(feat, 0.0),
                "shap_importance":         shap_scores.get(feat, 0.0),
            })
        df = pd.DataFrame(rows)

        def _minmax(s: pd.Series) -> pd.Series:
            lo, hi = s.min(), s.max()
            if (hi - lo) < _EPS:
                return pd.Series(np.zeros(len(s)), index=s.index)
            return (s - lo) / (hi - lo)

        df["mi_norm"]   = _minmax(df["mi_score"])
        df["mw_norm"]   = _minmax(df["mannwhitney_effect_size"])
        df["xgb_norm"]  = _minmax(df["xgb_importance"])
        df["shap_norm"] = _minmax(df["shap_importance"])

        df["composite_score"] = (
            df["mi_norm"] + df["mw_norm"] + df["xgb_norm"] + df["shap_norm"]
        ) / 4.0
        df["composite_score"] = df["composite_score"].round(6)
        df = df.sort_values("composite_score", ascending=False).reset_index(drop=True)
        df["composite_rank"] = df.index + 1

        for col, rank_col in [
            ("mi_score", "mi_rank"),
            ("mannwhitney_effect_size", "mannwhitney_rank"),
            ("xgb_importance", "xgb_rank"),
            ("shap_importance", "shap_rank"),
        ]:
            df[rank_col] = df[col].rank(ascending=False, method="min").astype(int)

        df["interpretation"]     = df["feature_name"].apply(self._generate_interpretation)
        df["retention_decision"] = df.apply(self._decide_retention, axis=1)
        df["method"]             = "composite(MI+MW+XGB+SHAP)"

        final_cols = [
            "composite_rank", "feature_name", "feature_group",
            "composite_score", "retention_decision", "method",
            "missingness_fraction", "pearson_corr", "spearman_corr",
            "mi_score", "mi_rank",
            "mannwhitney_pvalue", "mannwhitney_effect_size", "mannwhitney_rank",
            "xgb_importance", "xgb_rank",
            "shap_importance", "shap_rank",
            "interpretation",
        ]
        return df[[c for c in final_cols if c in df.columns]]

    # =========================================================================
    # Interpretation & Retention
    # =========================================================================

    def _generate_interpretation(self, feat: str) -> str:
        return _INTERPRETATIONS.get(
            feat,
            f"{_feature_group(feat).capitalize()} feature '{feat}': see feature dictionary for details.",
        )

    def _decide_retention(self, row: pd.Series) -> str:
        """
        REJECTED only when BOTH:
          - missingness_fraction > 30%
          - composite_score < 5%

        Low Pearson/Spearman is NEVER sufficient for rejection alone.
        """
        high_missing        = float(row["missingness_fraction"]) > MISSINGNESS_REJECT_THRESHOLD
        near_zero_composite = float(row["composite_score"])      < COMPOSITE_REJECT_THRESHOLD
        return "REJECTED" if (high_missing and near_zero_composite) else "RETAINED"

    # =========================================================================
    # Artifact Outputs
    # =========================================================================

    def _save_artifacts(
        self,
        ranking_df: pd.DataFrame,
        xgb_model: XGBClassifier,
        X: pd.DataFrame,
    ) -> None:
        """Write all 5 output artifacts to self.data_dir."""
        ranking_df.to_csv(self.ranking_csv_path, index=False)
        logger.info("[FeatureSelector] Saved feature_ranking.csv (%d rows)", len(ranking_df))
        self._save_importance_plot(ranking_df)
        top10 = self._build_top_n_json(ranking_df, 10)
        self.top10_path.write_text(json.dumps(top10, indent=2), encoding="utf-8")
        logger.info("[FeatureSelector] Saved top_10_features.json")
        top20 = self._build_top_n_json(ranking_df, 20)
        self.top20_path.write_text(json.dumps(top20, indent=2), encoding="utf-8")
        logger.info("[FeatureSelector] Saved top_20_features.json")
        report = self._build_full_report(ranking_df)
        self.report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        logger.info("[FeatureSelector] Saved feature_selection_report.json")

    def _save_importance_plot(self, ranking_df: pd.DataFrame) -> None:
        """4-panel dark-theme bar chart: XGBoost, SHAP, MI, Mann-Whitney top-30 features."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches

            top_n = min(30, len(ranking_df))
            plot_df = ranking_df.head(top_n).copy()
            features = plot_df["feature_name"].tolist()[::-1]

            def _norm(arr: np.ndarray) -> np.ndarray:
                lo, hi = arr.min(), arr.max()
                return np.zeros_like(arr) if (hi - lo) < _EPS else (arr - lo) / (hi - lo)

            xgb_vals  = _norm(plot_df["xgb_importance"].values[::-1])
            shap_vals = _norm(plot_df["shap_importance"].values[::-1])
            mi_vals   = _norm(plot_df["mi_score"].values[::-1])
            mw_vals   = _norm(plot_df["mannwhitney_effect_size"].values[::-1])
            retained  = (plot_df["retention_decision"] == "RETAINED").values[::-1]

            fig, axes = plt.subplots(1, 4, figsize=(24, max(10, top_n * 0.42)), sharey=True)
            fig.patch.set_facecolor("#0f1117")
            configs = [
                ("XGBoost Gain\nImportance",  xgb_vals,  "#4fc3f7"),
                ("SHAP Global\nImportance",   shap_vals, "#81c784"),
                ("Mutual\nInformation",       mi_vals,   "#ffb74d"),
                ("Mann-Whitney\nEffect Size", mw_vals,   "#ce93d8"),
            ]
            y_pos = np.arange(len(features))
            for ax, (title, vals, color) in zip(axes, configs):
                ax.set_facecolor("#1a1d27")
                bar_colors = [color if r else "#ef5350" for r in retained]
                ax.barh(y_pos, vals, color=bar_colors, edgecolor="none", height=0.65)
                ax.set_title(title, color="white", fontsize=10, fontweight="bold", pad=10)
                ax.set_xlim(0, 1.1)
                ax.tick_params(colors="white", labelsize=8)
                for spine in ("top", "right"):
                    ax.spines[spine].set_visible(False)
                ax.spines["left"].set_color("#444")
                ax.spines["bottom"].set_color("#444")
                ax.grid(axis="x", alpha=0.15, color="white", linestyle="--")
            axes[0].set_yticks(y_pos)
            axes[0].set_yticklabels(features, fontsize=8, color="white")
            retained_patch = mpatches.Patch(color="#4fc3f7", label="RETAINED")
            rejected_patch = mpatches.Patch(color="#ef5350", label="REJECTED")
            fig.legend(
                handles=[retained_patch, rejected_patch], loc="lower center", ncol=2,
                fontsize=10, facecolor="#1a1d27", edgecolor="#444", labelcolor="white",
                bbox_to_anchor=(0.5, -0.02),
            )
            fig.suptitle(
                "MuleDetector -- Feature Importance Comparison (Top 30)",
                fontsize=14, fontweight="bold", color="white", y=1.01,
            )
            plt.tight_layout(rect=[0, 0.03, 1, 1])
            plt.savefig(self.plot_path, dpi=150, bbox_inches="tight",
                        facecolor=fig.get_facecolor())
            plt.close(fig)
            logger.info("[FeatureSelector] Saved feature_importance_plot.png")
        except Exception as exc:
            logger.warning("[FeatureSelector] Plot generation failed: %s", exc)

    def _build_top_n_json(self, ranking_df: pd.DataFrame, n: int) -> List[Dict[str, Any]]:
        results = []
        for _, row in ranking_df.head(n).iterrows():
            results.append({
                "rank":               int(row["composite_rank"]),
                "feature_name":       str(row["feature_name"]),
                "feature_group":      str(row["feature_group"]),
                "importance":         round(float(row["composite_score"]), 6),
                "composite_score":    round(float(row["composite_score"]), 6),
                "method":             str(row["method"]),
                "interpretation":     str(row["interpretation"]),
                "retention_decision": str(row["retention_decision"]),
                "scores": {
                    "missingness_fraction":    round(float(row["missingness_fraction"]), 6),
                    "pearson_correlation":     round(float(row["pearson_corr"]), 6),
                    "spearman_correlation":    round(float(row["spearman_corr"]), 6),
                    "mutual_information":      round(float(row["mi_score"]), 8),
                    "mannwhitney_pvalue":      round(float(row["mannwhitney_pvalue"]), 8),
                    "mannwhitney_effect_size": round(float(row["mannwhitney_effect_size"]), 6),
                    "xgboost_gain_importance": round(float(row["xgb_importance"]), 8),
                    "shap_global_importance":  round(float(row["shap_importance"]), 8),
                },
                "ranks": {
                    "composite_rank":   int(row["composite_rank"]),
                    "mi_rank":          int(row["mi_rank"]),
                    "mannwhitney_rank": int(row["mannwhitney_rank"]),
                    "xgb_rank":         int(row["xgb_rank"]),
                    "shap_rank":        int(row["shap_rank"]),
                },
            })
        return results

    def _build_full_report(self, ranking_df: pd.DataFrame) -> Dict[str, Any]:
        retained_df = ranking_df[ranking_df["retention_decision"] == "RETAINED"]
        rejected_df = ranking_df[ranking_df["retention_decision"] == "REJECTED"]
        group_counts: Dict[str, int] = {}
        group_retained: Dict[str, int] = {}
        for grp in ranking_df["feature_group"].unique():
            grp_mask = ranking_df["feature_group"] == grp
            group_counts[grp]   = int(grp_mask.sum())
            group_retained[grp] = int(
                (grp_mask & (ranking_df["retention_decision"] == "RETAINED")).sum()
            )
        all_features_list = []
        for _, row in ranking_df.iterrows():
            all_features_list.append({
                "rank":               int(row["composite_rank"]),
                "feature_name":       str(row["feature_name"]),
                "feature_group":      str(row["feature_group"]),
                "composite_score":    round(float(row["composite_score"]), 6),
                "method":             str(row["method"]),
                "interpretation":     str(row["interpretation"]),
                "retention_decision": str(row["retention_decision"]),
                "missingness_fraction":       round(float(row["missingness_fraction"]), 6),
                "pearson_corr":               round(float(row["pearson_corr"]), 6),
                "spearman_corr":              round(float(row["spearman_corr"]), 6),
                "mi_score":                   round(float(row["mi_score"]), 8),
                "mi_rank":                    int(row["mi_rank"]),
                "mannwhitney_pvalue":         round(float(row["mannwhitney_pvalue"]), 8),
                "mannwhitney_effect_size":    round(float(row["mannwhitney_effect_size"]), 6),
                "mannwhitney_rank":           int(row["mannwhitney_rank"]),
                "xgb_importance":             round(float(row["xgb_importance"]), 8),
                "xgb_rank":                   int(row["xgb_rank"]),
                "shap_importance":            round(float(row["shap_importance"]), 8),
                "shap_rank":                  int(row["shap_rank"]),
            })
        return {
            "report_version": "1.0.0",
            "pipeline": "FeatureSelector -- MuleDetector",
            "methods_used": [
                "missingness_audit",
                "pearson_spearman_correlation (informational only, not in composite)",
                "mutual_information_classif",
                "mannwhitney_u_test",
                "xgboost_gain_importance",
                "shap_global_mean_abs_value",
            ],
            "composite_formula": "mean(norm(MI), norm(MW_effect_size), norm(XGB_gain), norm(SHAP))",
            "rejection_policy": (
                "REJECTED only when missingness_fraction > 0.30 AND composite_score < 0.05. "
                "Low Pearson/Spearman correlation is NEVER the sole rejection criterion."
            ),
            "summary": {
                "total_features_evaluated": int(len(ranking_df)),
                "features_retained":        int(len(retained_df)),
                "features_rejected":        int(len(rejected_df)),
                "features_by_group":        group_counts,
                "retained_by_group":        group_retained,
                "top_feature":              str(ranking_df.iloc[0]["feature_name"]) if len(ranking_df) > 0 else "",
                "top_composite_score":      round(float(ranking_df.iloc[0]["composite_score"]), 6) if len(ranking_df) > 0 else 0.0,
            },
            "top_10": self._build_top_n_json(ranking_df, 10),
            "top_20": self._build_top_n_json(ranking_df, 20),
            "all_features": all_features_list,
        }

    def _build_summary(
        self,
        ranking_df: pd.DataFrame,
        elapsed: float,
        has_supervised_label: bool,
        n_features: int,
    ) -> Dict[str, Any]:
        retained = int((ranking_df["retention_decision"] == "RETAINED").sum())
        rejected = int((ranking_df["retention_decision"] == "REJECTED").sum())
        top3 = [
            {
                "rank":    int(r["composite_rank"]),
                "feature": r["feature_name"],
                "score":   round(r["composite_score"], 6),
            }
            for _, r in ranking_df.head(3).iterrows()
        ]
        return {
            "status":                   "success",
            "elapsed_seconds":          elapsed,
            "supervised_label_used":    has_supervised_label,
            "total_features_evaluated": n_features,
            "features_retained":        retained,
            "features_rejected":        rejected,
            "top_3_features":           top3,
            "artifacts": {
                "feature_ranking_csv":      str(self.ranking_csv_path),
                "feature_importance_plot":  str(self.plot_path),
                "top_10_features_json":     str(self.top10_path),
                "top_20_features_json":     str(self.top20_path),
                "feature_selection_report": str(self.report_path),
            },
        }


# ---------------------------------------------------------------------------
# Convenience top-level function
# ---------------------------------------------------------------------------

def run_feature_selection(
    feature_df: pd.DataFrame,
    label_col: str = "is_mule_pattern",
    data_dir: Optional[pathlib.Path] = None,
) -> Dict[str, Any]:
    """Convenience wrapper around FeatureSelector.run()."""
    return FeatureSelector(data_dir=data_dir).run(feature_df, label_col=label_col)
