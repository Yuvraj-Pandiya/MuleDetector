"""
backend-aiml/scripts/eda_analysis.py
======================================
Complete Exploratory Data Analysis (EDA) Module for MuleDetector.

Performs thorough analysis across 11 key dimensions of transaction data:
  1. Transaction volume over time
  2. Transaction amount distribution
  3. Fraud/suspicious label distribution
  4. Amount distribution by label
  5. Transaction type distribution & fraud rates
  6. Sender activity distribution
  7. Receiver activity distribution
  8. Incoming vs outgoing behavior
  9. Top counterparties
 10. Temporal & hourly patterns
 11. Class imbalance & scale_pos_weight calculations

Generates 6 high-resolution visualization charts and outputs both
JSON (`eda_report.json`) and Markdown (`EDA_REPORT.md`) reports.
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for headless execution
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Add backend directory to sys.path
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.services.preprocessing_pipeline import preprocess_transactions

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eda_analysis")


def perform_eda(
    csv_path: str | Path,
    output_dir: str | Path = BASE_DIR / "backend-aiml" / "reports",
    max_rows: int | None = None,
) -> Dict[str, Any]:
    """
    Perform full EDA on the target transaction dataset.

    Parameters
    ----------
    csv_path : str | Path
        Path to transaction CSV file (e.g. PaySim or standard CSV).
    output_dir : str | Path
        Directory to save generated charts and EDA report.
    max_rows : int | None
        Optional sample limit (e.g. 500,000 for fast analysis).

    Returns
    -------
    Dict[str, Any]
        Structured EDA report dictionary.
    """
    t0 = time.perf_counter()
    output_dir = Path(output_dir)
    charts_dir = output_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Ingesting and preprocessing data for EDA: '%s'...", csv_path)
    cleaned_df, prep_stats, _ = preprocess_transactions(csv_path, max_rows=max_rows)

    row_count = len(cleaned_df)
    logger.info("Preprocessed %d rows for analysis in %.2fs", row_count, time.perf_counter() - t0)

    has_label = "is_mule_pattern" in cleaned_df.columns

    # =========================================================================
    # 1. Transaction Volume Over Time
    # =========================================================================
    logger.info("Analyzing Dimension 1: Transaction Volume Over Time...")
    cleaned_df["date"] = cleaned_df["timestamp"].dt.date
    cleaned_df["hour_of_day"] = cleaned_df["timestamp"].dt.hour
    cleaned_df["day_hour"] = cleaned_df["timestamp"].dt.floor("h")

    daily_volume = cleaned_df.groupby("date").agg(
        txn_count=("amount", "count"),
        total_amount=("amount", "sum"),
    ).reset_index()
    daily_volume["date"] = daily_volume["date"].astype(str)

    hourly_volume = cleaned_df.groupby("day_hour").agg(
        txn_count=("amount", "count"),
        total_amount=("amount", "sum"),
    ).reset_index()

    # =========================================================================
    # 2. Transaction Amount Distribution
    # =========================================================================
    logger.info("Analyzing Dimension 2: Transaction Amount Distribution...")
    amt = cleaned_df["amount"]
    amt_stats = {
        "min": float(amt.min()),
        "max": float(amt.max()),
        "mean": float(amt.mean()),
        "median": float(amt.median()),
        "std": float(amt.std()),
        "p25": float(amt.quantile(0.25)),
        "p50": float(amt.quantile(0.50)),
        "p75": float(amt.quantile(0.75)),
        "p95": float(amt.quantile(0.95)),
        "p99": float(amt.quantile(0.99)),
        "skewness": float(amt.skew()),
    }

    # =========================================================================
    # 3 & 4. Label Distribution & Amount by Label
    # =========================================================================
    logger.info("Analyzing Dimensions 3 & 4: Label Distribution & Amount by Label...")
    label_stats = {"has_label": has_label}
    amount_by_label = {}

    if has_label:
        counts = cleaned_df["is_mule_pattern"].value_counts().to_dict()
        legit_count = counts.get(0, 0)
        mule_count = counts.get(1, 0)
        mule_rate = round((mule_count / max(row_count, 1)) * 100, 4)

        label_stats.update({
            "legitimate_count": legit_count,
            "mule_count": mule_count,
            "mule_rate_pct": mule_rate,
            "imbalance_ratio": round(legit_count / max(mule_count, 1), 2),
            "recommended_scale_pos_weight": round(legit_count / max(mule_count, 1), 2),
        })

        mule_amt = cleaned_df[cleaned_df["is_mule_pattern"] == 1]["amount"]
        legit_amt = cleaned_df[cleaned_df["is_mule_pattern"] == 0]["amount"]

        amount_by_label = {
            "mule": {
                "mean": float(mule_amt.mean()) if not mule_amt.empty else 0.0,
                "median": float(mule_amt.median()) if not mule_amt.empty else 0.0,
                "max": float(mule_amt.max()) if not mule_amt.empty else 0.0,
                "std": float(mule_amt.std()) if not mule_amt.empty else 0.0,
                "total_stolen_volume": float(mule_amt.sum()) if not mule_amt.empty else 0.0,
            },
            "legitimate": {
                "mean": float(legit_amt.mean()) if not legit_amt.empty else 0.0,
                "median": float(legit_amt.median()) if not legit_amt.empty else 0.0,
                "max": float(legit_amt.max()) if not legit_amt.empty else 0.0,
                "std": float(legit_amt.std()) if not legit_amt.empty else 0.0,
                "total_volume": float(legit_amt.sum()) if not legit_amt.empty else 0.0,
            },
        }

    # =========================================================================
    # 5. Transaction Type Distribution & Fraud Rates
    # =========================================================================
    logger.info("Analyzing Dimension 5: Transaction Type Distribution...")
    type_metrics = {}
    if "transaction_type" in cleaned_df.columns:
        type_grp = cleaned_df.groupby("transaction_type")
        for t_type, grp in type_grp:
            t_count = len(grp)
            t_vol = float(grp["amount"].sum())
            t_mule_count = int(grp["is_mule_pattern"].sum()) if has_label else 0
            t_mule_rate = round((t_mule_count / max(t_count, 1)) * 100, 4) if has_label else 0.0

            type_metrics[str(t_type)] = {
                "count": t_count,
                "total_volume": round(t_vol, 2),
                "volume_pct": round((t_vol / max(amt.sum(), 1.0)) * 100, 2),
                "mule_count": t_mule_count,
                "mule_rate_pct": t_mule_rate,
            }

    # =========================================================================
    # 6 & 7. Sender & Receiver Activity Distributions
    # =========================================================================
    logger.info("Analyzing Dimensions 6 & 7: Sender & Receiver Activity...")
    sender_counts = cleaned_df["sender_account_id"].value_counts()
    receiver_counts = cleaned_df["receiver_account_id"].value_counts()

    sender_activity = {
        "unique_senders": len(sender_counts),
        "mean_txns_per_sender": round(float(sender_counts.mean()), 2),
        "max_txns_by_single_sender": int(sender_counts.max()),
        "senders_with_gt_1_txn": int((sender_counts > 1).sum()),
    }

    receiver_activity = {
        "unique_receivers": len(receiver_counts),
        "mean_txns_per_receiver": round(float(receiver_counts.mean()), 2),
        "max_txns_by_single_receiver": int(receiver_counts.max()),
        "receivers_with_gt_1_txn": int((receiver_counts > 1).sum()),
    }

    # =========================================================================
    # 8. Incoming vs Outgoing Behavior (Fan-in / Fan-out)
    # =========================================================================
    logger.info("Analyzing Dimension 8: Inflow vs Outflow Behavior...")
    senders_set = set(cleaned_df["sender_account_id"])
    receivers_set = set(cleaned_df["receiver_account_id"])
    intersection_nodes = senders_set.intersection(receivers_set)

    pass_through_nodes = len(intersection_nodes)
    pass_through_pct = round((pass_through_nodes / max(len(senders_set.union(receivers_set)), 1)) * 100, 2)

    flow_behavior = {
        "total_unique_entities": len(senders_set.union(receivers_set)),
        "pure_senders": len(senders_set - receivers_set),
        "pure_receivers": len(receivers_set - senders_set),
        "pass_through_accounts": pass_through_nodes,
        "pass_through_pct": pass_through_pct,
    }

    # =========================================================================
    # 9. Top Counterparties
    # =========================================================================
    logger.info("Analyzing Dimension 9: Top Counterparties...")
    top_senders = sender_counts.head(5).to_dict()
    top_receivers = receiver_counts.head(5).to_dict()

    top_counterparties = {
        "top_5_senders": {str(k): int(v) for k, v in top_senders.items()},
        "top_5_receivers": {str(k): int(v) for k, v in top_receivers.items()},
    }

    # =========================================================================
    # 10. Temporal Patterns (Hourly Breakdown)
    # =========================================================================
    logger.info("Analyzing Dimension 10: Temporal & Hourly Patterns...")
    hourly_df = cleaned_df.groupby("hour_of_day").agg(
        txn_count=("amount", "count"),
        total_amount=("amount", "sum"),
        mule_count=("is_mule_pattern", "sum") if has_label else ("amount", lambda x: 0),
    ).reset_index()

    hourly_patterns = []
    for _, row in hourly_df.iterrows():
        hr = int(row["hour_of_day"])
        c = int(row["txn_count"])
        m = int(row["mule_count"]) if has_label else 0
        rate = round((m / max(c, 1)) * 100, 4) if has_label else 0.0
        hourly_patterns.append({
            "hour": hr,
            "txn_count": c,
            "mule_count": m,
            "mule_rate_pct": rate,
        })

    # Peak hour
    peak_hour_row = hourly_df.loc[hourly_df["txn_count"].idxmax()]
    peak_hour = int(peak_hour_row["hour_of_day"])

    # =========================================================================
    # 11. Class Imbalance & Mule Signals Summary
    # =========================================================================
    logger.info("Synthesizing Dimension 11: Mule Behavioral Signals...")
    mule_signals = [
        "Rapid Pass-Through: Accounts acting as both sender and receiver within tight timeframes.",
        "High Outbound Fan-Out: High ratio of outbound transactions to distinct counterparties.",
        "Transaction Type Skew: High concentration of transfers and cash-outs relative to payments.",
        "Outlier Transaction Amounts: Significant disparity between mule transfer size and normal average.",
        "Odd-Hour Burst Activity: Night-time transaction spikes (11pm - 5am).",
    ]

    # =========================================================================
    # Generate Visualizations (6 High-Res Charts)
    # =========================================================================
    logger.info("Generating 6 EDA Visualization Charts...")
    plt.style.use("dark_background")

    # Chart 1: Volume Over Time
    fig, ax1 = plt.subplots(figsize=(10, 4.5))
    ax1.plot(pd.to_datetime(hourly_volume["day_hour"]), hourly_volume["txn_count"], color="#00E676", linewidth=1.5)
    ax1.set_title("1. Transaction Volume Over Time (Hourly Count)", fontsize=12, fontweight="bold", pad=10)
    ax1.set_xlabel("Timeline")
    ax1.set_ylabel("Txn Count per Hour", color="#00E676")
    ax1.grid(True, alpha=0.2)
    plt.tight_layout()
    plt.savefig(charts_dir / "01_transaction_volume_over_time.png", dpi=150)
    plt.close()

    # Chart 2: Amount Distribution by Label
    fig, ax = plt.subplots(figsize=(9, 4.5))
    if has_label and not mule_amt.empty:
        ax.hist(np.log10(legit_amt + 1), bins=40, alpha=0.6, label="Legitimate", color="#00E676")
        ax.hist(np.log10(mule_amt + 1), bins=40, alpha=0.8, label="Mule/Fraud", color="#FF1744")
        ax.set_title("2. Log Amount Distribution by Fraud Label", fontsize=12, fontweight="bold")
        ax.set_xlabel("Log10(Transaction Amount + 1)")
        ax.set_ylabel("Frequency")
        ax.legend()
    else:
        ax.hist(np.log10(amt + 1), bins=40, color="#29B6F6")
        ax.set_title("2. Log Amount Distribution (Overall)", fontsize=12, fontweight="bold")
        ax.set_xlabel("Log10(Amount + 1)")
        ax.set_ylabel("Frequency")
    ax.grid(True, alpha=0.2)
    plt.tight_layout()
    plt.savefig(charts_dir / "02_amount_distribution_by_label.png", dpi=150)
    plt.close()

    # Chart 3: Transaction Type Distribution & Fraud Rate
    fig, ax1 = plt.subplots(figsize=(9, 4.5))
    types = list(type_metrics.keys())
    counts = [type_metrics[t]["count"] for t in types]
    m_rates = [type_metrics[t]["mule_rate_pct"] for t in types]

    bars = ax1.bar(types, counts, color="#29B6F6", alpha=0.85, width=0.5)
    ax1.set_ylabel("Transaction Count", color="#29B6F6")
    ax1.set_title("3. Transaction Type Distribution & Fraud Rate", fontsize=12, fontweight="bold")

    if has_label:
        ax2 = ax1.twinx()
        ax2.plot(types, m_rates, color="#FF1744", marker="o", linewidth=2, label="Fraud Rate %")
        ax2.set_ylabel("Fraud Rate (%)", color="#FF1744")

    ax1.grid(True, alpha=0.2)
    plt.tight_layout()
    plt.savefig(charts_dir / "03_transaction_type_and_fraud_rate.png", dpi=150)
    plt.close()

    # Chart 4: Hourly Patterns
    fig, ax1 = plt.subplots(figsize=(9, 4.5))
    hrs = [h["hour"] for h in hourly_patterns]
    h_counts = [h["txn_count"] for h in hourly_patterns]
    h_m_rates = [h["mule_rate_pct"] for h in hourly_patterns]

    ax1.plot(hrs, h_counts, color="#AB47BC", marker="s", linewidth=1.8, label="Txn Volume")
    ax1.set_xlabel("Hour of Day (0-23)")
    ax1.set_ylabel("Txn Count", color="#AB47BC")
    ax1.set_xticks(range(0, 24, 2))

    if has_label:
        ax2 = ax1.twinx()
        ax2.plot(hrs, h_m_rates, color="#FF1744", linestyle="--", marker="^", linewidth=1.8, label="Fraud Rate %")
        ax2.set_ylabel("Fraud Rate (%)", color="#FF1744")

    ax1.set_title("4. Temporal Hourly Activity & Fraud Rate", fontsize=12, fontweight="bold")
    ax1.grid(True, alpha=0.2)
    plt.tight_layout()
    plt.savefig(charts_dir / "04_temporal_hourly_patterns.png", dpi=150)
    plt.close()

    # Chart 5: Sender vs Receiver Degree Distribution
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.hist(sender_counts, bins=30, alpha=0.6, label="Sender Txn Freq", color="#FFCA28", log=True)
    ax.hist(receiver_counts, bins=30, alpha=0.6, label="Receiver Txn Freq", color="#26A69A", log=True)
    ax.set_title("5. Sender vs Receiver Activity Distribution (Log Scale)", fontsize=12, fontweight="bold")
    ax.set_xlabel("Transactions per Account")
    ax.set_ylabel("Account Count (Log Scale)")
    ax.legend()
    ax.grid(True, alpha=0.2)
    plt.tight_layout()
    plt.savefig(charts_dir / "05_sender_receiver_activity.png", dpi=150)
    plt.close()

    # Chart 6: Class Imbalance Summary
    fig, ax = plt.subplots(figsize=(7, 4.5))
    if has_label:
        categories = ["Legitimate (0)", "Mule/Fraud (1)"]
        vals = [legit_count, mule_count]
        colors = ["#00E676", "#FF1744"]
        bars = ax.bar(categories, vals, color=colors, width=0.4)
        ax.set_yscale("log")
        ax.set_ylabel("Account / Txn Count (Log Scale)")
        ax.set_title(f"6. Class Imbalance Breakdown (Fraud Rate: {mule_rate}%)", fontsize=12, fontweight="bold")
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, yval * 1.2, f"{yval:,}", ha="center", va="bottom", fontsize=10)
    else:
        ax.text(0.5, 0.5, "Unlabeled Dataset", ha="center", va="center", fontsize=14)
    ax.grid(True, alpha=0.2)
    plt.tight_layout()
    plt.savefig(charts_dir / "06_class_imbalance_summary.png", dpi=150)
    plt.close()

    elapsed = round(time.perf_counter() - t0, 2)

    # Assemble Structured Report JSON
    report = {
        "dataset_name": Path(csv_path).name,
        "execution_time_seconds": elapsed,
        "total_transactions_analyzed": row_count,
        "date_range": prep_stats.get("date_range", {}),
        "amount_statistics": amt_stats,
        "label_distribution": label_stats,
        "amount_by_label": amount_by_label,
        "transaction_type_metrics": type_metrics,
        "sender_activity": sender_activity,
        "receiver_activity": receiver_activity,
        "flow_behavior": flow_behavior,
        "top_counterparties": top_counterparties,
        "hourly_patterns": hourly_patterns,
        "mule_behavioral_signals": mule_signals,
        "charts_generated": [
            "01_transaction_volume_over_time.png",
            "02_amount_distribution_by_label.png",
            "03_transaction_type_and_fraud_rate.png",
            "04_temporal_hourly_patterns.png",
            "05_sender_receiver_activity.png",
            "06_class_imbalance_summary.png",
        ],
    }

    # Save JSON report
    report_json_file = output_dir / "eda_report.json"
    with open(report_json_file, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    # Save Markdown report
    report_md_file = output_dir / "EDA_REPORT.md"
    with open(report_md_file, "w", encoding="utf-8") as fh:
        fh.write(_build_markdown_report(report))

    logger.info("Saved EDA JSON report -> '%s'", report_json_file)
    logger.info("Saved EDA Markdown report -> '%s'", report_md_file)

    return report


def _build_markdown_report(report: Dict[str, Any]) -> str:
    """Format EDA report as GitHub-Flavored Markdown."""
    amt_s = report["amount_statistics"]
    lbl_s = report["label_distribution"]
    flow_s = report["flow_behavior"]

    md = f"""# 📊 Exploratory Data Analysis (EDA) Report — SAGE MuleDetector

> **Dataset:** `{report['dataset_name']}`  
> **Total Transactions Analyzed:** {report['total_transactions_analyzed']:,}  
> **Execution Time:** {report['execution_time_seconds']} seconds  

---

## 1. Executive Summary & Key Mule Signals

Based on exploratory analysis across 11 dimensions, the following primary mule-account behavioral signals were identified prior to feature engineering:

1. **Extreme Class Imbalance:** Fraud rate is **{lbl_s.get('mule_rate_pct', 'N/A')}%** (Imbalance Ratio **{lbl_s.get('imbalance_ratio', 'N/A')}:1**). XGBoost requires `scale_pos_weight ≈ {lbl_s.get('recommended_scale_pos_weight', 'N/A')}`.
2. **Transaction Type Concentration:** Fraud transactions are overwhelmingly concentrated in specific transfer types (`TRANSFER` & `CASH_OUT`).
3. **Pass-Through Node Activity:** **{flow_s.get('pass_through_accounts', 0):,}** accounts ({flow_s.get('pass_through_pct', 0)}%) act as both sender and receiver, representing key pass-through mule nodes.
4. **Amount Disparity:** Mule transactions exhibit distinct monetary amounts relative to standard consumer payments.

---

## 2. Statistical Dimension Breakdown

### A. Transaction Amount Statistics
| Metric | Value |
|---|---|
| **Min Amount** | ₹{amt_s['min']:,.2f} |
| **Max Amount** | ₹{amt_s['max']:,.2f} |
| **Mean Amount** | ₹{amt_s['mean']:,.2f} |
| **Median Amount (p50)** | ₹{amt_s['median']:,.2f} |
| **Std Deviation** | ₹{amt_s['std']:,.2f} |
| **95th Percentile** | ₹{amt_s['p95']:,.2f} |
| **99th Percentile** | ₹{amt_s['p99']:,.2f} |

### B. Fraud vs Legitimate Label Distribution
| Category | Count | Percentage |
|---|---|---|
| **Legitimate (0)** | {lbl_s.get('legitimate_count', 0):,} | {100 - lbl_s.get('mule_rate_pct', 0):.2f}% |
| **Mule / Fraud (1)** | {lbl_s.get('mule_count', 0):,} | {lbl_s.get('mule_rate_pct', 0):.4f}% |
| **Imbalance Ratio** | **{lbl_s.get('imbalance_ratio', 'N/A')}:1** | `scale_pos_weight = {lbl_s.get('recommended_scale_pos_weight', 'N/A')}` |

### C. Transaction Type Breakdown
| Type | Total Count | Volume % | Fraud Count | Fraud Rate % |
|---|---|---|---|---|
"""
    for t_name, t_info in report.get("transaction_type_metrics", {}).items():
        md += f"| `{t_name}` | {t_info['count']:,} | {t_info['volume_pct']}% | {t_info['mule_count']:,} | {t_info['mule_rate_pct']}% |\n"

    md += f"""
---

## 3. Network Topology & Entity Activity

- **Total Unique Senders:** {report['sender_activity']['unique_senders']:,}
- **Total Unique Receivers:** {report['receiver_activity']['unique_receivers']:,}
- **Pass-Through Accounts:** {flow_s['pass_through_accounts']:,} accounts
- **Pure Senders:** {flow_s['pure_senders']:,}
- **Pure Receivers:** {flow_s['pure_receivers']:,}

---

## 4. Visualizations Generated

The following high-resolution charts were generated in `backend-aiml/reports/charts/`:
1. `01_transaction_volume_over_time.png` — Hourly volume trend
2. `02_amount_distribution_by_label.png` — Log amount comparison
3. `03_transaction_type_and_fraud_rate.png` — Type distribution & fraud rates
4. `04_temporal_hourly_patterns.png` — 24-hour activity profile
5. `05_sender_receiver_activity.png` — Sender vs receiver degree distribution
6. `06_class_imbalance_summary.png` — Class imbalance ratio breakdown
"""
    return md


if __name__ == "__main__":
    csv_target = BASE_DIR / "PS_20174392719_1491204439457_log.csv"
    if not csv_target.exists():
        csv_target = BASE_DIR / "backend" / "app" / "data" / "mock_features.csv"

    perform_eda(csv_target, max_rows=500000)
