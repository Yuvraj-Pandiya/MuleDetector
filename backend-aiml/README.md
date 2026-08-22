# Backend-AIML — SAGE ML Pipeline & Data Science

Standalone ML training pipeline, data generation scripts, acceptance tests, and feature schema documentation for the SAGE Mule Detector.

## What's Here

| Folder | Contents |
|---|---|
| `scripts/` | Data generation, model training scripts, E2E tests |
| `docs/` | Feature schema contract, ML design docs |
| `data/` | Placeholder for generated artefacts (gitignored) |

## ML Techniques Used

### 1. Feature Engineering (21 features from raw transactions)
- **Velocity** — `txn_count_1h/24h/7d`, `total_amount_out/in_24h`, `avg/max_transaction_amount`
- **Behavioral** — `avg_time_to_forward_funds_minutes`, `ratio_received_to_sent_24h`, `account_age_days`
- **Graph/Network** — `in_degree`, `out_degree`, `betweenness_centrality`, `is_in_short_cycle`, `fan_in/out_ratio`
- **Anomaly** — `amount_zscore_avg`, `round_number_txn_ratio`, `odd_hour_txn_ratio`

### 2. Supervised Classification — XGBoost
- `scale_pos_weight` for 95/5 class imbalance
- Regularised: `min_child_weight=5`, `reg_lambda=2`, `reg_alpha=0.1`
- Stratified 80/20 train/test split
- **Metrics: ROC-AUC=0.836, Precision=0.889, Recall=0.667, F1=0.762**

### 3. Unsupervised Fallback — Isolation Forest
- Activated when no ground-truth labels exist (cold-start scenario)
- `contamination=0.05` matching expected mule rate

### 4. Explainable AI — SHAP
- `shap.TreeExplainer` for per-account feature attribution
- Graceful fallback to XGBoost `feature_importances_` (no heavy shap dependency needed)

## Scripts

```bash
cd backend-aiml

# Generate synthetic mock data (1000 accounts, ~5% mule rate)
python scripts/generate_mock_features.py

# Generate sample transactions.csv for testing
python scripts/generate_sample.py

# Inject realistic mule patterns into existing transactions
python scripts/inject_mule_patterns.py

# Run E2E acceptance test (requires backend running at localhost:8000)
python scripts/e2e_audit.py

# Run B3/B4/B5 acceptance tests
python scripts/test_b3_acceptance.py
python scripts/test_b4_acceptance.py
python scripts/test_b5_acceptance.py

# Verify graph feature signal quality
python scripts/verify_graph_signals.py
```

## Requirements

```bash
pip install -r requirements-ml.txt
```

## Feature Schema

See [`docs/feature_schema.md`](docs/feature_schema.md) for the full 23-column contract agreed between the data-pipeline team (Track A) and the ML team (Track B).
