"""
app/services/model_benchmarker.py
===================================
Model Benchmarking Pipeline for MuleDetector.

Trains and evaluates 3 models on identical train/test splits:
  1. Logistic Regression (with StandardScaler & balanced class weights)
  2. Random Forest (with balanced class weights)
  3. XGBoost (with scale_pos_weight)

Metrics evaluated:
  - Precision
  - Recall
  - F1-Score
  - ROC-AUC
  - PR-AUC (Average Precision)
  - Confusion Matrix (TN, FP, FN, TP)

Explicitly analyzes Precision-Recall tradeoffs under class imbalance and
recommends the best model based on PR-AUC & F1-Score (NEVER accuracy alone).

Artifacts generated in app/data/:
  - model_comparison.csv
  - model_comparison_chart.png
  - model_benchmark_report.json

Public API
----------
ModelBenchmarker(data_dir).run(feature_df, label_col) -> dict
run_model_benchmark(feature_df, label_col, data_dir)  -> dict
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
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

logger = logging.getLogger(__name__)

_EPS = 1e-12
RANDOM_SEED = 42
TEST_SIZE = 0.20


class ModelBenchmarker:
    """
    Model Benchmarking Engine comparing Logistic Regression, Random Forest, and XGBoost.
    """

    def __init__(self, data_dir: Optional[pathlib.Path] = None) -> None:
        if data_dir is None:
            data_dir = pathlib.Path(__file__).parent.parent / "data"
        self.data_dir = pathlib.Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.csv_path = self.data_dir / "model_comparison.csv"
        self.plot_path = self.data_dir / "model_comparison_chart.png"
        self.report_path = self.data_dir / "model_benchmark_report.json"

    # =========================================================================
    # Public Entry Point
    # =========================================================================

    def run(
        self,
        feature_df: pd.DataFrame,
        label_col: str = "is_mule_pattern",
        train_ratio: float = 0.6,
        val_ratio: float = 0.2,
        test_ratio: float = 0.2,
        random_state: int = RANDOM_SEED,
        split_strategy: str = "auto",
    ) -> Dict[str, Any]:
        """
        Run model benchmarking across Logistic Regression, Random Forest, and XGBoost.

        Parameters
        ----------
        feature_df : pd.DataFrame
            Account-level feature matrix.
        label_col : str
            Binary target column.
        train_ratio : float
            Proportion of data used for training (default 0.6).
        val_ratio : float
            Proportion of data used for validation (default 0.2).
        test_ratio : float
            Proportion of data used for testing (default 0.2).
        random_state : int
            Random seed for reproducibility.
        split_strategy : str
            "auto", "temporal", or "stratified".

        Returns
        -------
        dict
            Summary report of benchmark results & recommendations.
        """
        t0 = time.perf_counter()
        logger.info("[ModelBenchmarker] Starting benchmark pipeline on %d rows", len(feature_df))

        # 1. Detect time column & determine split strategy
        time_col_candidates = ["first_transaction_time", "last_transaction_time", "timestamp", "step", "time"]
        time_col = next((c for c in time_col_candidates if c in feature_df.columns), None)

        use_temporal = (split_strategy == "temporal") or (split_strategy == "auto" and time_col is not None)

        if use_temporal and time_col is not None:
            logger.info("[ModelBenchmarker] Executing TEMPORAL (chronological) split on column '%s'", time_col)
            sorted_df = feature_df.sort_values(by=time_col).reset_index(drop=True)
        else:
            if split_strategy == "temporal" and time_col is None:
                logger.warning("[ModelBenchmarker] Temporal split requested but no timestamp column found. Falling back to stratified.")
            use_temporal = False
            sorted_df = feature_df.copy()

        # 2. Isolate feature columns & target label
        exclude_cols = {
            "account_id", label_col, "fraud_label", "label", "target",
            "anomaly_score", "anomaly_flag", "anomaly_percentile",
            "first_transaction_time", "last_transaction_time", "timestamp", "step", "time"
        }
        feature_cols = [
            c for c in sorted_df.columns
            if c not in exclude_cols and pd.api.types.is_numeric_dtype(sorted_df[c])
        ]

        if not feature_cols:
            raise ValueError("[ModelBenchmarker] No valid numeric feature columns found.")

        X = sorted_df[feature_cols].fillna(0.0).copy()
        y, has_supervised = self._resolve_labels(sorted_df, label_col, X)

        # 3. Train / Validation / Test Split Logic
        n_total = len(sorted_df)
        if use_temporal and time_col is not None:
            n_train = int(n_total * train_ratio)
            n_val = int(n_total * val_ratio)

            X_train, y_train = X.iloc[:n_train], y[:n_train]
            X_val, y_val = X.iloc[n_train:n_train + n_val], y[n_train:n_train + n_val]
            X_test, y_test = X.iloc[n_train + n_val:], y[n_train + n_val:]

            train_period = {
                "start": str(sorted_df[time_col].iloc[0]),
                "end": str(sorted_df[time_col].iloc[n_train - 1]),
            }
            val_period = {
                "start": str(sorted_df[time_col].iloc[n_train]),
                "end": str(sorted_df[time_col].iloc[n_train + n_val - 1]),
            }
            test_period = {
                "start": str(sorted_df[time_col].iloc[n_train + n_val]),
                "end": str(sorted_df[time_col].iloc[-1]),
            }
            actual_split_strategy = "temporal"
        else:
            X_temp, X_test, y_temp, y_test = train_test_split(
                X, y,
                test_size=test_ratio,
                random_state=random_state,
                stratify=y if len(np.unique(y)) > 1 else None,
            )
            val_relative = val_ratio / (train_ratio + val_ratio)
            X_train, X_val, y_train, y_val = train_test_split(
                X_temp, y_temp,
                test_size=val_relative,
                random_state=random_state,
                stratify=y_temp if len(np.unique(y_temp)) > 1 else None,
            )
            train_period = {"start": "N/A (Random Split)", "end": "N/A"}
            val_period = {"start": "N/A (Random Split)", "end": "N/A"}
            test_period = {"start": "N/A (Random Split)", "end": "N/A"}
            actual_split_strategy = "stratified"

        # Class distributions
        def calc_class_dist(y_arr: np.ndarray) -> Dict[str, Any]:
            tot = len(y_arr)
            pos = int((y_arr == 1).sum())
            neg = int((y_arr == 0).sum())
            pct = round((pos / max(tot, 1)) * 100.0, 2)
            return {"total": tot, "positive_mules": pos, "negative_legit": neg, "mule_percentage": pct}

        class_distribution = {
            "train": calc_class_dist(y_train),
            "validation": calc_class_dist(y_val),
            "test": calc_class_dist(y_test),
        }

        n_pos_train = class_distribution["train"]["positive_mules"]
        n_neg_train = class_distribution["train"]["negative_legit"]
        spw = max(float(n_neg_train) / max(n_pos_train, 1), 1.0)

        logger.info(
            "[ModelBenchmarker] Strategy: %s | Train: %d (pos=%d, neg=%d) | Val: %d | Test: %d",
            actual_split_strategy, len(y_train), n_pos_train, n_neg_train, len(y_val), len(y_test),
        )

        # 4. Define Models
        models: Dict[str, Any] = {
            "Logistic Regression": Pipeline([
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=random_state,
                )),
            ]),
            "Random Forest": RandomForestClassifier(
                n_estimators=100,
                max_depth=8,
                class_weight="balanced",
                random_state=random_state,
                n_jobs=-1,
            ),
            "XGBoost": XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.7,
                min_child_weight=5,
                scale_pos_weight=spw,
                random_state=random_state,
                eval_metric="logloss",
                verbosity=0,
            ),
        }

        # 5. Fit & Evaluate Models
        results: List[Dict[str, Any]] = []
        pr_curves: Dict[str, Dict[str, List[float]]] = {}

        for name, model in models.items():
            t_start = time.perf_counter()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model.fit(X_train.values if isinstance(model, XGBClassifier) else X_train, y_train)

            t_fit = time.perf_counter() - t_start

            # Validation Predictions & Metrics
            X_val_eval = X_val.values if isinstance(model, XGBClassifier) else X_val
            val_pred = model.predict(X_val_eval)
            val_prob = model.predict_proba(X_val_eval)[:, 1] if hasattr(model, "predict_proba") else val_pred.astype(float)
            val_prec = round(float(precision_score(y_val, val_pred, zero_division=0)), 4)
            val_rec = round(float(recall_score(y_val, val_pred, zero_division=0)), 4)
            val_f1 = round(float(f1_score(y_val, val_pred, zero_division=0)), 4)
            try:
                val_roc = round(float(roc_auc_score(y_val, val_prob)), 4)
            except Exception:
                val_roc = 0.5
            try:
                val_pr_auc = round(float(average_precision_score(y_val, val_prob)), 4)
            except Exception:
                val_pr_auc = 0.0

            # Test Predictions & Metrics (Final Evaluation)
            X_test_eval = X_test.values if isinstance(model, XGBClassifier) else X_test
            y_pred = model.predict(X_test_eval)
            if hasattr(model, "predict_proba"):
                y_prob = model.predict_proba(X_test_eval)[:, 1]
            else:
                y_prob = y_pred.astype(float)

            prec = round(float(precision_score(y_test, y_pred, zero_division=0)), 4)
            rec = round(float(recall_score(y_test, y_pred, zero_division=0)), 4)
            f1 = round(float(f1_score(y_test, y_pred, zero_division=0)), 4)

            try:
                roc = round(float(roc_auc_score(y_test, y_prob)), 4)
            except Exception:
                roc = 0.5

            try:
                pr_auc = round(float(average_precision_score(y_test, y_prob)), 4)
            except Exception:
                pr_auc = 0.0

            cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
            tn, fp, fn, tp = [int(v) for v in cm.ravel()]

            # Precision-Recall Curve points
            p_curve, r_curve, th_curve = precision_recall_curve(y_test, y_prob)
            pr_curves[name] = {
                "precision": [round(float(v), 4) for v in p_curve],
                "recall": [round(float(v), 4) for v in r_curve],
                "thresholds": [round(float(v), 4) for v in th_curve],
            }

            # Threshold Tradeoff Table (evaluating cutoffs 0.1 to 0.9)
            threshold_tradeoffs = self._analyze_threshold_tradeoffs(y_test, y_prob)

            results.append({
                "model_name": name,
                "precision": prec,
                "recall": rec,
                "f1_score": f1,
                "roc_auc": roc,
                "pr_auc": pr_auc,
                "tn": tn,
                "fp": fp,
                "fn": fn,
                "tp": tp,
                "val_precision": val_prec,
                "val_recall": val_rec,
                "val_f1_score": val_f1,
                "val_roc_auc": val_roc,
                "val_pr_auc": val_pr_auc,
                "training_time_seconds": round(t_fit, 3),
                "threshold_tradeoffs": threshold_tradeoffs,
            })

        # 6. Best Model Recommendation Logic (PR-AUC & F1 driven)
        best_model_name = max(results, key=lambda r: (r["pr_auc"], r["f1_score"]))["model_name"]

        for r in results:
            r["is_recommended"] = (r["model_name"] == best_model_name)

        # 7. Save Artifacts
        ranking_df = pd.DataFrame(results)[
            ["model_name", "precision", "recall", "f1_score", "roc_auc", "pr_auc",
             "tn", "fp", "fn", "tp", "val_pr_auc", "val_f1_score", "training_time_seconds", "is_recommended"]
        ]
        ranking_df.to_csv(self.csv_path, index=False)

        self._save_comparison_chart(results, pr_curves)

        dataset_temporal_limitations = [
            "PaySim logs span a constrained timeframe of 744 steps (~31 days), limiting long-term seasonality modeling.",
            "Chronological splitting tests performance on future time horizons, exposing models to potential temporal concept drift.",
            "Class imbalance and nocturnal transaction frequency fluctuate across different time periods, requiring dynamic decision thresholds.",
            "Short observation windows may restrict graph centrality metrics from discovering long-evolving mule syndicates."
        ]

        report = {
            "report_version": "1.1.0",
            "pipeline": "ModelBenchmarker -- MuleDetector",
            "split_strategy": actual_split_strategy,
            "time_column_used": time_col if actual_split_strategy == "temporal" else None,
            "supervised_label_used": has_supervised,
            "temporal_periods": {
                "train_period": train_period,
                "validation_period": val_period,
                "test_period": test_period,
            },
            "class_distribution": class_distribution,
            "dataset_temporal_limitations": dataset_temporal_limitations,
            "best_model_recommendation": {
                "recommended_model": best_model_name,
                "selection_metric": "PR-AUC (Precision-Recall Area Under Curve)",
                "rationale": (
                    f"Selected {best_model_name} under {actual_split_strategy} validation because PR-AUC evaluates positive-class "
                    "detection performance under severe class imbalance without inflation from true negatives. "
                    "Accuracy is explicitly rejected because a trivial model predicting 100% legitimate accounts "
                    "would achieve high accuracy while catching zero mules."
                ),
            },
            "model_results": results,
        }

        self.report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        elapsed = round(time.perf_counter() - t0, 3)
        logger.info("[ModelBenchmarker] Completed benchmark (%s) in %.3fs. Recommended: %s", actual_split_strategy, elapsed, best_model_name)

        return {
            "status": "success",
            "split_strategy": actual_split_strategy,
            "elapsed_seconds": elapsed,
            "best_model": best_model_name,
            "models_evaluated": [r["model_name"] for r in results],
            "temporal_periods": {
                "train_period": train_period,
                "validation_period": val_period,
                "test_period": test_period,
            },
            "class_distribution": class_distribution,
            "dataset_temporal_limitations": dataset_temporal_limitations,
            "artifacts": {
                "model_comparison_csv": str(self.csv_path),
                "model_comparison_chart": str(self.plot_path),
                "model_benchmark_report": str(self.report_path),
            },
        }

    # =========================================================================
    # Helpers
    # =========================================================================

    def _resolve_labels(
        self,
        feature_df: pd.DataFrame,
        label_col: str,
        X: pd.DataFrame,
    ) -> Tuple[np.ndarray, bool]:
        if label_col in feature_df.columns:
            unique_vals = feature_df[label_col].dropna().unique()
            if len(unique_vals) >= 2:
                y = feature_df[label_col].fillna(0).astype(int).values
                return y, True

        # Fallback proxy labels
        iso = IsolationForest(n_estimators=100, contamination=0.05, random_state=42, n_jobs=-1)
        iso.fit(X.fillna(0.0).values)
        raw_preds = iso.predict(X.fillna(0.0).values)
        y = (raw_preds == -1).astype(int)
        return y, False

    def _analyze_threshold_tradeoffs(
        self,
        y_true: np.ndarray,
        y_prob: np.ndarray,
    ) -> List[Dict[str, Any]]:
        tradeoffs = []
        for cutoff in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
            pred = (y_prob >= cutoff).astype(int)
            p = round(float(precision_score(y_true, pred, zero_division=0)), 4)
            r = round(float(recall_score(y_true, pred, zero_division=0)), 4)
            f = round(float(f1_score(y_true, pred, zero_division=0)), 4)
            tradeoffs.append({
                "threshold": cutoff,
                "precision": p,
                "recall": r,
                "f1_score": f,
            })
        return tradeoffs

    def _save_comparison_chart(
        self,
        results: List[Dict[str, Any]],
        pr_curves: Dict[str, Dict[str, List[float]]],
    ) -> None:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
            fig.patch.set_facecolor("#0f1117")

            model_names = [r["model_name"] for r in results]
            x_pos = np.arange(len(model_names))
            width = 0.15

            metrics_data = [
                ("Precision", [r["precision"] for r in results], "#4fc3f7"),
                ("Recall", [r["recall"] for r in results], "#ffb74d"),
                ("F1-Score", [r["f1_score"] for r in results], "#81c784"),
                ("ROC-AUC", [r["roc_auc"] for r in results], "#ce93d8"),
                ("PR-AUC", [r["pr_auc"] for r in results], "#f48fb1"),
            ]

            ax1.set_facecolor("#1a1d27")
            for i, (name, vals, color) in enumerate(metrics_data):
                offset = (i - 2) * width
                ax1.bar(x_pos + offset, vals, width, label=name, color=color)

            ax1.set_xticks(x_pos)
            ax1.set_xticklabels(model_names, color="white", fontweight="bold")
            ax1.set_ylim(0, 1.1)
            ax1.set_title("Model Metrics Comparison", color="white", fontweight="bold", pad=10)
            ax1.tick_params(colors="white")
            ax1.grid(axis="y", alpha=0.15, color="white", linestyle="--")
            ax1.legend(facecolor="#1a1d27", edgecolor="#444", labelcolor="white", fontsize=8)

            # Panel 2: Precision-Recall Curves
            ax2.set_facecolor("#1a1d27")
            colors = {"Logistic Regression": "#4fc3f7", "Random Forest": "#81c784", "XGBoost": "#f48fb1"}

            for name, curve in pr_curves.items():
                p_vals = curve["precision"]
                r_vals = curve["recall"]
                c = colors.get(name, "#ffffff")
                pr_auc_val = next(r["pr_auc"] for r in results if r["model_name"] == name)
                ax2.plot(r_vals, p_vals, label=f"{name} (PR-AUC={pr_auc_val})", color=c, linewidth=2)

            ax2.set_xlabel("Recall", color="white")
            ax2.set_ylabel("Precision", color="white")
            ax2.set_xlim(0, 1.05)
            ax2.set_ylim(0, 1.05)
            ax2.set_title("Precision-Recall Curves", color="white", fontweight="bold", pad=10)
            ax2.tick_params(colors="white")
            ax2.grid(alpha=0.15, color="white", linestyle="--")
            ax2.legend(facecolor="#1a1d27", edgecolor="#444", labelcolor="white", fontsize=8)

            for ax in (ax1, ax2):
                for spine in ("top", "right"):
                    ax.spines[spine].set_visible(False)
                ax.spines["left"].set_color("#444")
                ax.spines["bottom"].set_color("#444")

            fig.suptitle("MuleDetector -- Model Benchmarking & PR Tradeoff Analysis",
                         fontsize=14, fontweight="bold", color="white", y=1.02)
            plt.tight_layout()
            plt.savefig(self.plot_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
            plt.close(fig)
            logger.info("[ModelBenchmarker] Saved model_comparison_chart.png")
        except Exception as exc:
            logger.warning("[ModelBenchmarker] Chart generation failed: %s", exc)


def run_model_benchmark(
    feature_df: pd.DataFrame,
    label_col: str = "is_mule_pattern",
    data_dir: Optional[pathlib.Path] = None,
    train_ratio: float = 0.6,
    val_ratio: float = 0.2,
    test_ratio: float = 0.2,
    random_state: int = RANDOM_SEED,
    split_strategy: str = "auto",
) -> Dict[str, Any]:
    """Convenience wrapper for ModelBenchmarker.run()."""
    return ModelBenchmarker(data_dir=data_dir).run(
        feature_df,
        label_col=label_col,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
        test_ratio=test_ratio,
        random_state=random_state,
        split_strategy=split_strategy,
    )
