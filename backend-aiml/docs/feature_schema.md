# Feature Schema Contract — MuleDetector

> **Version**: 0.1.0  
> **Status**: Agreed ✅  
> **Owner**: Both teams (data-pipeline + ml-api)  
> **Last updated**: 2026-08-20

---

## Overview

This document is the **single source of truth** for the feature matrix that the
data-pipeline outputs and the ML-API consumes.  Every column listed here must
be present in the CSV / DataFrame handed off between the two sub-systems.
Breaking changes require a version bump and sign-off from both team members.

---

## Feature Matrix

One row per `account_id`.

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `account_id` | `str` | No | Unique account identifier (primary key of the row). |

### Velocity Features

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `txn_count_1h` | `int` | No | Number of transactions in the last 1 hour. |
| `txn_count_24h` | `int` | No | Number of transactions in the last 24 hours. |
| `txn_count_7d` | `int` | No | Number of transactions in the last 7 days. |
| `total_amount_out_24h` | `float` | No | Total outbound amount (currency units) in the last 24 hours. |
| `total_amount_in_24h` | `float` | No | Total inbound amount (currency units) in the last 24 hours. |
| `avg_transaction_amount` | `float` | No | Average single-transaction amount over the look-back window. |
| `max_transaction_amount` | `float` | No | Maximum single-transaction amount over the look-back window. |

### Behavioral Features

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `ratio_received_to_sent_24h` | `float` | No | `total_amount_in_24h / (total_amount_out_24h + ε)`. High ratio is a mule signal. |
| `avg_time_to_forward_funds_minutes` | `float` | No | Average elapsed minutes between receiving funds and forwarding them onward. |
| `unique_counterparty_count` | `int` | No | Distinct counterparties transacted with in the look-back window. |
| `account_age_days` | `int` | No | Days since the account was opened. |
| `is_new_high_volume_flag` | `int` | No | `1` if account is <30 days old **and** `txn_count_7d > threshold`, else `0`. |

### Graph Features

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `in_degree` | `int` | No | Number of unique accounts sending funds **to** this account (transaction graph). |
| `out_degree` | `int` | No | Number of unique accounts receiving funds **from** this account. |
| `is_in_short_cycle` | `int` | No | `1` if account participates in a directed cycle of length ≤ 4, else `0`. |
| `betweenness_centrality` | `float` | No | Betweenness centrality score in the transaction graph (NetworkX convention). |
| `fan_in_ratio` | `float` | No | `in_degree / (in_degree + out_degree + ε)`. |
| `fan_out_ratio` | `float` | No | `out_degree / (in_degree + out_degree + ε)`. |

### Anomaly Features

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `amount_zscore_avg` | `float` | No | Z-score of `avg_transaction_amount` relative to peer accounts. |
| `round_number_txn_ratio` | `float` | No | Fraction of transactions whose amount is a round number (e.g. divisible by 100). |
| `odd_hour_txn_ratio` | `float` | No | Fraction of transactions occurring between 00:00–05:59 local time. |

### Label (optional)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `is_mule_pattern` | `int` | **Yes** | Ground-truth label: `1` = confirmed mule pattern, `0` = benign. **Absent when no labeled data is available** (inference mode). |

---

## Column Count Summary

| Group | Count |
|-------|-------|
| Key | 1 |
| Velocity | 7 |
| Behavioral | 5 |
| Graph | 6 |
| Anomaly | 3 |
| Label | 1 |
| **Total** | **23** |

---

## Data Types & Constraints

- All `int` columns must be `≥ 0`.
- All `float` columns must be finite (no `NaN`, `inf`). Use `0.0` as a safe
  default for missing windows.
- `is_*` flag columns are encoded as `int` `{0, 1}` — **not** Python `bool` —
  for compatibility with scikit-learn and XGBoost.
- `account_id` is a UTF-8 string; do **not** cast to int.

---

## Versioning Policy

Any change to column names, types, or semantics constitutes a **breaking
change** and must be:
1. Discussed and agreed by both team members.
2. Reflected here with a version bump.
3. Committed on `main` before either branch diverges further.
