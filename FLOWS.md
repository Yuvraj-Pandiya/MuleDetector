# 🔄 MuleScope End-to-End User Flow & Backend Code Mapping

This document provides a step-by-step trace of every user-facing feature in the **MuleScope** dashboard, mapping it directly to the backend Python files and services where the ML calculations, databases, and graph math are executed.

---

## 🗺️ E2E Flow Map: UI Feature ➔ Backend Code Mapping

```
[ User Interaction ] ➔ [ API Endpoint ] ➔ [ Python Implementation File ]
```

---

### 1. Ingestion & Schema Alignment Flow
*   **User Action**: Investigator navigates to the **Upload** page, drops a raw transaction CSV file (which might have different column names like `From_Account` instead of `sender_account_id`), and provides a dataset name.
*   **User View**: Inspects confidence match percentages for columns, validates mapping, and clicks "Confirm Mapping & Register Dataset."
*   **Backend Trace**:
    *   `POST /upload-dataset/preview` maps columns using:
        *   [`backend/app/routers/upload.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/routers/upload.py) — Handles the upload routes and preview payloads.
        *   [`backend/app/services/schema/profiler.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/services/schema/profiler.py) — Injects the column parser and infers data types.
        *   [`backend/app/services/schema/mapper.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/services/schema/mapper.py) — Fuzzy matches columns using token metrics.
    *   `POST /upload-dataset/confirm` converts and saves the CSV using:
        *   [`backend/app/services/schema/normalizer.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/services/schema/normalizer.py) — Sanitizes rows, checks mandatory AML fields, and generates data quality reports.

---

### 2. Multi-Dataset Registry & Persistence
*   **User Action**: Investigator switches between **PaySim Benchmark** and custom uploaded banking logs via the navbar dropdown.
*   **User View**: All counts, alert queues, graphs, and statistics across every page reload update instantly.
*   **Backend Trace**:
    *   `GET /datasets` and `POST /datasets/{id}/activate` are managed by:
        *   [`backend/app/routers/datasets.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/routers/datasets.py) — The REST router endpoints for listing, switching, and deleting datasets.
        *   [`backend/app/services/dataset_registry.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/services/dataset_registry.py) — Registers dataset metadata into `dataset_registry.json` and updates the active file token (`active_upload.json`).
        *   [`backend/app/main.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/main.py) — Validates registry health on application boot.

---

### 3. Interactive Network Graph & Cycle Detection
*   **User Action**: Investigator clicks **Graph** in the navbar, selects an account, and adjusts filtering parameters (min amount, time window).
*   **User View**: A directed force-graph renders, showing counterparties colored by risk tier, with critical money laundering rings and transaction loops highlighted.
*   **Backend Trace**:
    *   `GET /graph/{account_id}` constructs the network topology using:
        *   [`backend/app/routers/graph.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/routers/graph.py) — Extracts directed neighbors and component structures.
        *   [`backend/app/services/features_graph.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/services/features_graph.py) — Calculates structural centralities and PageRank weights.
        *   [`backend/app/services/features_mule_flow.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/services/features_mule_flow.py) — Evaluates cyclic loop participation by calculating adjacency matrix powers ($\text{diag}(A^2 + A^3 + A^4)$).

---

### 4. Explainable AI (XAI) & SHAP Attributions
*   **User Action**: Investigator clicks **Explainability** in the navbar and searches for a specific suspicious account.
*   **User View**: A local SHAP waterfall chart renders, showing which features pushed the account score up or down, accompanied by human-readable explanation bullet points.
*   **Backend Trace**:
    *   `GET /predict/explain/{account_id}` runs attribution logic using:
        *   [`backend/app/routers/predict.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/routers/predict.py) — Serves the explanation payload.
        *   [`backend/app/services/explainer.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/services/explainer.py) — Initialises TreeSHAP explainer, extracts model weights, and converts feature statistics into plain-English reasons (e.g. *94% of inbound volume was transferred out within 5 minutes*).

---

### 5. Compliance Alerts Queue & HITL Feedback Loop
*   **User Action**: Investigator clicks **Alerts** in the navbar, selects an open alert, changes its status (e.g. to "Confirmed Mule"), and writes an audit note.
*   **User View**: The alert status changes, the dashboard KPI updates, and the feedback log displays the user's note.
*   **Backend Trace**:
    *   `POST /alerts/generate` scores features and triggers alerts using:
        *   [`backend/app/services/alert_generator.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/services/alert_generator.py) — Bootstrap the SQLite `alerts` table in `alerts.db` and writes alert profiles.
    *   `POST /feedback` registers investigator action using:
        *   [`backend/app/routers/feedback.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/routers/feedback.py) — REST endpoints for feedback submission.
        *   [`backend/app/services/feedback_store.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/services/feedback_store.py) — Connects to SQLite `feedback.db` and logs the audit trail.

---

### 6. Unsupervised Anomaly Detection
*   **User Action**: Investigator clicks **Anomaly** in the navbar.
*   **User View**: Inspects the outlier rate, score histogram, and lists anomalous accounts flagged without relying on historical labels.
*   **Backend Trace**:
    *   `GET /predict/anomalies` runs anomaly analysis using:
        *   [`backend/app/services/anomaly_detector.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/services/anomaly_detector.py) — Fits an unsupervised `IsolationForest` model, runs KS-test statistical validation, and yields anomaly scores.

---

### 7. Feature Rank & Selection
*   **User Action**: Investigator clicks **Features** in the navbar.
*   **User View**: Inspects feature importance charts, correlation matrices, and mutual information scores.
*   **Backend Trace**:
    *   `GET /feature-selection/ranking` processes variables using:
        *   [`backend/app/routers/feature_selection.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/routers/feature_selection.py) — Serves the feature selector results.
        *   [`backend/app/services/feature_selector.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/services/feature_selector.py) — Runs ANOVA F-tests, correlation threshold checks, Mutual Information, and Random Forest feature selection pipelines.

---

### 8. Suspicious Activity Report (SAR) Filing
*   **User Action**: Investigator clicks **"Generate SAR"** on a flagged account card.
*   **User View**: A modal opens with a pre-filled compliance narrative. Clicking file saves the SAR to the system and allows PDF export.
*   **Backend Trace**:
    *   `POST /sar` and `GET /sar/account/{account_id}` file reports using:
        *   [`backend/app/routers/sar.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/routers/sar.py) — Endpoint routes.
        *   [`backend/app/services/sar_store.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/services/sar_store.py) — Writes finalized SAR text narratives and metadata to the SQLite `sar.db` database.

---

### 9. Model Monitoring & Drift Metrics
*   **User Action**: Investigator clicks **Monitoring** in the navbar and adjusts drift warning thresholds.
*   **User View**: Displays Population Stability Index (PSI) drift indicators comparing current inputs against the baseline model.
*   **Backend Trace**:
    *   `GET /train/performance` and `GET /feedback/summary` run metrics using:
        *   [`backend/app/services/drift_detector.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/services/drift_detector.py) — Computes PSI and distribution shifts.
        *   [`backend/app/services/model_trainer.py`](file:///c:/Users/swaya/OneDrive/Desktop/Squid%20Hack/backend/app/services/model_trainer.py) — Fits baseline XGBoost models and evaluates training metrics.
