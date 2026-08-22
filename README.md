# SAGE — Mule Detector Intelligence Platform

> AI-powered Anti-Money Laundering (AML) system for detecting money mule accounts using ML, graph analysis, and explainable AI.

## Repository Structure

```
MuleDetector/
├── frontend/        ← React + Vite UI (deploy to Vercel/Netlify)
├── backend/         ← FastAPI REST API + ML services (deploy to Railway/Render/Docker)
└── backend-aiml/    ← Standalone ML scripts, data generation, acceptance tests
```

## Quick Start

```bash
# 1. Start Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 2. Start Frontend (new terminal)
cd frontend
npm install
npm run dev

# 3. Open → http://localhost:5173
```

## What It Does

- **Scores 1,000+ accounts** for mule probability using XGBoost (ROC-AUC: 0.836)
- **Explains every flag** with SHAP feature attribution + human-readable reasons
- **Detects mule rings** via transaction network graph analysis
- **Manages compliance cases** with SQLite-backed alert queue (OPEN → REVIEWED → DISMISSED)
- **Full analyst UI** — Dashboard, Alerts, Accounts, Explainability, Graph, Metrics

## Branches

| Branch | Purpose |
|---|---|
| `main` | Full integrated project |
| `feature/frontend` | Frontend-only code |
| `feature/backend` | Backend API-only code |
| `feature/backend-aiml` | ML pipeline scripts only |

## Docs
- [`backend/README.md`](backend/README.md) — API endpoints, deployment
- [`frontend/README.md`](frontend/README.md) — UI setup, environment variables
- [`backend-aiml/README.md`](backend-aiml/README.md) — ML techniques, scripts
- [`backend-aiml/docs/feature_schema.md`](backend-aiml/docs/feature_schema.md) — 21-feature contract
