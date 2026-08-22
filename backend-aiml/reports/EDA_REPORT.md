# 📊 Exploratory Data Analysis (EDA) Report — SAGE MuleDetector

> **Dataset:** `PS_20174392719_1491204439457_log.csv`  
> **Total Transactions Analyzed:** 500,000  
> **Execution Time:** 7.06 seconds  

---

## 1. Executive Summary & Key Mule Signals

Based on exploratory analysis across 11 dimensions, the following primary mule-account behavioral signals were identified prior to feature engineering:

1. **Extreme Class Imbalance:** Fraud rate is **0.0466%** (Imbalance Ratio **2144.92:1**). XGBoost requires `scale_pos_weight ≈ 2144.92`.
2. **Transaction Type Concentration:** Fraud transactions are overwhelmingly concentrated in specific transfer types (`TRANSFER` & `CASH_OUT`).
3. **Pass-Through Node Activity:** **6** accounts (0.0%) act as both sender and receiver, representing key pass-through mule nodes.
4. **Amount Disparity:** Mule transactions exhibit distinct monetary amounts relative to standard consumer payments.

---

## 2. Statistical Dimension Breakdown

### A. Transaction Amount Statistics
| Metric | Value |
|---|---|
| **Min Amount** | ₹0.10 |
| **Max Amount** | ₹10,000,000.00 |
| **Mean Amount** | ₹166,393.69 |
| **Median Amount (p50)** | ₹81,375.60 |
| **Std Deviation** | ₹272,584.08 |
| **95th Percentile** | ₹543,246.30 |
| **99th Percentile** | ₹1,396,246.90 |

### B. Fraud vs Legitimate Label Distribution
| Category | Count | Percentage |
|---|---|---|
| **Legitimate (0)** | 499,767 | 99.95% |
| **Mule / Fraud (1)** | 233 | 0.0466% |
| **Imbalance Ratio** | **2144.92:1** | `scale_pos_weight = 2144.92` |

### C. Transaction Type Breakdown
| Type | Total Count | Volume % | Fraud Count | Fraud Rate % |
|---|---|---|---|---|
| `CASH_IN` | 109,319 | 22.84% | 0 | 0.0% |
| `CASH_OUT` | 182,316 | 41.09% | 121 | 0.0664% |
| `DEBIT` | 3,603 | 0.03% | 0 | 0.0% |
| `PAYMENT` | 164,032 | 2.29% | 0 | 0.0% |
| `TRANSFER` | 40,730 | 33.75% | 112 | 0.275% |

---

## 3. Network Topology & Entity Activity

- **Total Unique Senders:** 499,953
- **Total Unique Receivers:** 214,856
- **Pass-Through Accounts:** 6 accounts
- **Pure Senders:** 499,947
- **Pure Receivers:** 214,850

---

## 4. Visualizations Generated

The following high-resolution charts were generated in `backend-aiml/reports/charts/`:
1. `01_transaction_volume_over_time.png` — Hourly volume trend
2. `02_amount_distribution_by_label.png` — Log amount comparison
3. `03_transaction_type_and_fraud_rate.png` — Type distribution & fraud rates
4. `04_temporal_hourly_patterns.png` — 24-hour activity profile
5. `05_sender_receiver_activity.png` — Sender vs receiver degree distribution
6. `06_class_imbalance_summary.png` — Class imbalance ratio breakdown
