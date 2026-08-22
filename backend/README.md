# Backend — SAGE Mule Detector API

FastAPI REST backend for the SAGE Anti-Money Laundering Mule Detection platform.

## Stack
- **FastAPI** — async Python REST API
- **XGBoost** — supervised mule classification model
- **scikit-learn** — IsolationForest fallback + metrics
- **NetworkX + scipy** — graph feature computation
- **SQLite** — alert persistence (zero-infrastructure)
- **joblib** — model serialisation

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `POST` | `/train` | Train XGBoost on feature data |
| `GET` | `/predict/risk-scores` | Score all accounts (sorted by risk desc) |
| `GET` | `/predict/explain/{id}` | SHAP explanation for one account |
| `POST` | `/alerts/generate` | Generate alerts for high-risk accounts |
| `GET` | `/alerts` | List alerts (filter by severity/status) |
| `PATCH` | `/alerts/{id}` | Update alert status (REVIEWED/DISMISSED) |
| `GET` | `/dashboard/summary` | Aggregated KPIs for dashboard |
| `GET` | `/graph/{account_id}` | Transaction network topology |
| `GET` | `/features` | Raw feature matrix |
| `POST` | `/upload-dataset` | Upload real transactions.csv |

**Swagger UI:** `http://localhost:8000/docs`

## Setup

```bash
cd backend
pip install -r requirements.txt

# Generate mock data (first time)
python -c "import sys; sys.path.insert(0, '.'); from scripts.generate_mock_features import main; main()"

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app + middleware + router registration
│   ├── routers/
│   │   ├── train.py         # POST /train
│   │   ├── predict.py       # GET /predict/*
│   │   ├── alerts.py        # GET/PATCH /alerts
│   │   ├── dashboard.py     # GET /dashboard/summary
│   │   ├── graph.py         # GET /graph/{id}
│   │   ├── features.py      # GET /features
│   │   ├── upload.py        # POST /upload-dataset
│   │   └── health.py        # GET /health
│   └── services/
│       ├── model_trainer.py      # XGBoost + IsolationForest training
│       ├── risk_scorer.py        # Account scoring + risk tier bucketing
│       ├── explainer.py          # SHAP/feature-importance XAI
│       ├── alert_generator.py    # Alert creation + SQLite persistence
│       ├── feature_pipeline.py   # Feature engineering orchestrator
│       ├── features_velocity.py  # Txn velocity features
│       ├── features_behavioral.py# Behavioral pattern features
│       ├── features_graph.py     # Graph/network features (NetworkX)
│       ├── features_anomaly.py   # Statistical anomaly features
│       └── data_loader.py        # CSV ingestion utilities
├── data/
│   └── .gitkeep             # model.pkl, metrics.json, alerts.db go here (gitignored)
├── requirements.txt
└── Dockerfile
```

## Deployment

**Railway / Render / AWS:**
```
Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Docker:**
```bash
docker build -t sage-backend .
docker run -p 8000:8000 sage-backend
```

## Data Files (not in git — generated at runtime)
| File | How to generate |
|---|---|
| `data/model.pkl` | `POST /train` |
| `data/metrics.json` | `POST /train` |
| `data/alerts.db` | `POST /alerts/generate` |
| `data/mock_features.csv` | See `backend-aiml/scripts/generate_mock_features.py` |
