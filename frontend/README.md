# Frontend — SAGE Mule Detector UI

React + Vite frontend for the SAGE Anti-Money Laundering Mule Detection platform.

## Stack
- **React 18** + **Vite** — fast SPA with HMR
- **Axios** — HTTP client hitting the FastAPI backend
- **Vanilla CSS** — dark-mode premium UI, no CSS framework

## Pages
| Page | Route | Purpose |
|---|---|---|
| Dashboard | `/dashboard` | KPI cards, risk distribution, 14-day alert trend |
| Alerts | `/alerts` | Case management queue (Open/Reviewed/Dismissed) |
| Accounts | `/accounts` | Risk-ranked account registry |
| Explainability | `/explain?id=ACC0...` | SHAP feature attribution + human-readable reason |
| Graph | `/graph` | Force-directed transaction network topology |
| Metrics | `/metrics` | Model performance (ROC-AUC, Precision, Recall, F1) |
| Upload | `/upload` | Upload real transaction CSV to retrain model |
| Simulation | `/simulation` | Simulate transaction risk scoring |

## Setup

```bash
cd frontend
npm install
npm run dev        # Development: http://localhost:5173
npm run build      # Production build → dist/
```

## Environment

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Backend FastAPI URL |

Create a `.env` file to override:
```
VITE_API_URL=https://your-backend.railway.app
```

## Deployment

**Vercel / Netlify:**
- Build command: `npm run build`
- Output directory: `dist`
- Set `VITE_API_URL` environment variable to your deployed backend URL
