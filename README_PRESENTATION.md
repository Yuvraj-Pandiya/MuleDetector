# 📊 MuleScope Presentation Deck Storyboard (12-Page Slide Outline & Prompt)

This file contains the complete slide-by-slide storyboard prompt for your money mule detection project presentation (**MuleScope**). You can use this markdown file as a visual design layout outline or copy-paste it directly into AI slide generators (such as *Gamma.app*, *Tome*, *ChatGPT*, or *Slidebean*).

---

## 🎨 Global Presentation Theme & Styling Guidelines
*   **Design Aesthetic**: Cyber-security theme. Minimalist glassmorphism with neon accents on matte slate.
*   **Palette**: Deep Slate Background (`#0B0F19`), Electric Cyan (`#0EA5E9`), Alert Rose (`#F43F5E`) for risks, and Emerald Green (`#10B981`) for safety/compliance.
*   **Typography**: *Outfit* for headers, *Inter* or *Fira Code* for monospace data metrics.

---

## 📽️ Slide-by-Slide Prompt Storyboard

### 🎴 Slide 1: Title Slide (The Hook)
*   **Visual**: Sleek, dark-mode screen featuring a central glowing cyber-shield network graph.
*   **Slide Header**: **MuleScope: Anti-Money Laundering (AML) Intelligence Platform**
*   **Sub-Header**: *Autonomous Money Mule Detection via Multi-Signal ML Models & Real-Time Network Graph Analytics*
*   **Key Points**:
    *   **Core Objective**: Transforming banking transaction monitoring from reactive rule-based thresholds to autonomous, graph-aware machine learning engines.
    *   **Core Technology Pillars**:
        *   📊 Multi-Dimensional Feature Engineering (74 features)
        *   🧠 Hybrid Machine Learning (Supervised XGBoost + Unsupervised Isolation Forest)
        *   Network Graph Topology (PageRank, Cycle Detection, Weakly Connected Components)
    *   **Engine Version**: Production v2.5

---

### ⚠️ Slide 2: The Problem (Problem Statement)
*   **Visual**: A split slide comparing legacy bank configurations with organized fraud evasion.
*   **Slide Header**: **The Money Mule Evasion Crisis**
*   **Key Points**:
    *   **Rule-Based Blindness**: Legacy monitoring relies on static transaction thresholds (e.g., flag transfers $> ₹200,000$). Fraud syndicates bypass these easily by slicing transactions into smaller amounts (smurfing).
    *   **Disposable Account Lifecycle**: Fraudsters hijack accounts, execute rapid pass-through transfers, and abandon the account within hours—long before traditional batch rule checks execute.
    *   **Structural Blindness**: Standard banking systems evaluate transactions in isolation. They are blind to multi-hop cyclic transfers, fan-in pooling networks, and dense money laundering loops (Mule Rings).

---

### 💡 Slide 3: The Solution (High-Level Engine Architecture)
*   **Visual**: A horizontal flowchart outlining the processing layers.
*   **Slide Header**: **Multi-Signal Hybrid ML Architecture**
*   **Key Points**:
    *   **Layer 1: Schema Ingestion & Mapping**: Universal CSV profiler normalizes bank schemas to canonical headers.
    *   **Layer 2: Feature Engineering Engine**: Extracts behavioral, velocity, temporal, and graph features.
    *   **Layer 3: Multi-Signal ML Scorer**: Combines:
        1.  *Supervised XGBoost* (trained on known historical fraud labels).
        2.  *Unsupervised Isolation Forest* (detects zero-day anomalies and unknown patterns).
        3.  *Network Graph Scoring* (evaluates centrality, PageRank, and cyclic risks).
    *   **Layer 4: Explainability & Actionable Alerts**: Local SHAP attributions convert scores into natural language compliance explanations.

---

### 📥 Slide 4: Data Ingestion, Schema Normalization & Imbalance Mitigation
*   **Visual**: Table illustrating data validation checks next to a class imbalance chart.
*   **Slide Header**: **Ingestion, Validation & Class Imbalance Compensation**
*   **Key Points**:
    *   **Canonical Mapping**: Automatically normalizes source fields (`nameOrig` $\rightarrow$ `sender_id`, `nameDest` $\rightarrow$ `receiver_id`, `step` $\rightarrow$ `timestamp`).
    *   **Ingestion Safety Guardrails**: Deduplication, positive amount validation, and strict temporal chronology sorting to prevent model data leakage.
    *   **Extreme Class Imbalance**: Labeled fraud rate is only **0.0466%** (imbalance ratio of **2,144 : 1**). Compensated using custom training parameters (`scale_pos_weight` in XGBoost) to maintain high sensitivity.

---

### 📊 Slide 5: The 74-Dimensional Feature Engineering Matrix
*   **Visual**: A radar chart or icon grid highlighting the 5 primary feature dimensions.
*   **Slide Header**: **Multi-Dimensional Behavior Profiling**
*   **Key Points**:
    *   **Velocity (17 features)**: Transaction frequency & volumes across rolling windows (5m, 15m, 1h, 6h, 24h, 7d).
    *   **Mule Fund Flow (10 features)**: Tracks FIFO money drain ratios and percentage of incoming funds transferred out within a 5-minute window.
    *   **Behavioral Ratios (20 features)**: Coefficient of variation, nocturnal transfer ratios, weekend activity, and new-account balance drops.
    *   **Temporal Velocity Change (7 features)**: Current 1h velocity divided by 24h baseline to identify newly activated sleeper accounts.
    *   **Graph/Topology (20 features)**: Out-degree, in-degree, PageRank, and network centrality scores.

---

### 🤖 Slide 6: Unsupervised Anomaly Detection Layer
*   **Visual**: A distribution curve showing normal scores in green, overlapping with anomalous score peaks in red.
*   **Slide Header**: **Unsupervised Isolation Forest Layer**
*   **Key Points**:
    *   **Zero-Day Threat Detection**: Isolation Forest runs strictly without relying on known labels, identifying novel transaction anomalies.
    *   **Outputs**: Produces continuous `anomaly_score` $[0.0, 1.0]$ and binary flags.
    *   **Statistical Alignment**: Alignment with labels is validated using 2-sample Kolmogorov-Smirnov ($D_{\text{stat}}$) and Mann-Whitney U testing.
    *   **Hyperparameter Tuning**: Auto-calibrated contamination factor ($0.1\% \dots 10.0\%$) tuned via cross-validation.

---

### 🕸️ Slide 7: Network Graph Analytics & Cycle Detection
*   **Visual**: A network graph diagram showing a clear multi-node loop highlighted in alert red.
*   **Slide Header**: **Graph Topology & Cycle Detection**
*   **Key Points**:
    *   **Sparse Matrix Cycle Engine**: Multi-hop feedback loop detection (e.g. A $\rightarrow$ B $\rightarrow$ C $\rightarrow$ A) calculated using adjacency matrix exponentiation ($\text{diag}(A^2 + A^3 + A^4)$) in $<1$ second.
    *   **Centrality Algorithms**: PageRank identifies money aggregators; Betweenness Centrality identifies intermediary routing accounts (money mules).
    *   **Mule Ring Extraction**: Clusters subgraphs using weakly connected components, filtering for high density ($\ge 0.15$) and cycle ratios ($\ge 30\%$) to group related mule rings.

---

### 📈 Slide 8: Supervised Risk Classification & Calibration
*   **Layout**: Calibration curve graph showing predicted probability vs true fraction of fraud.
*   **Slide Header**: **Supervised XGBoost Scoring Engine**
*   **Key Points**:
    *   **Model**: Gradient Boosted Decision Trees (XGBoost) optimized for highly non-linear tabular features.
    *   **Target Calibration**: Risk scores outputted on a standard scale ($0.0 \dots 100.0$).
    *   **Risk Tiers**: Calibrated boundaries classify accounts into:
        *   🔴 **Critical Risk** ($\ge 85.0$)
        *   🟠 **High Risk** ($70.0 - 85.0$)
        *   🟡 **Medium Risk** ($30.0 - 70.0$)
        *   🟢 **Low Risk** ($< 30.0$)

---

### 💡 Slide 9: Explainable AI (XAI) & Attributions
*   **Visual**: A SHAP Force Plot visualization showing features pushing risk score from base value to high.
*   **Slide Header**: **Explainable AI (XAI) & Transparency**
*   **Key Points**:
    *   **Compliance Transparency**: Integrates SHAP (SHapley Additive exPlanations) to turn black-box ML decisions into audit trails.
    *   **Global Importance**: Shows that cycle involvement and rapid forwarding ratios are the model's strongest predictors.
    *   **Local Attribution**: Clicking any account dynamically generates top contributor reasons (e.g. *Account is part of 3-hop transaction loop*, *94% of inbound volume was transferred out within 5 minutes*).

---

### ⚙️ Slide 10: Infrastructure, Deployment & Technology Stack
*   **Visual**: A system diagram mapping frontend deployment, backend hosting, and data layers.
*   **Slide Header**: **Production-Ready Tech Stack**
*   **Key Points**:
    *   **FastAPI Backend**: Asynchronous python backend hosted on **Render** utilizing multiprocessing workers.
    *   **React Frontend**: High-fidelity glassmorphism-themed monitoring console deployed on **Vercel**.
    *   **Database**: SQLite (`alerts.db`, `feedback.db`, `sar.db`) running in Write-Ahead Logging (WAL) mode.
    *   **Performance**: Sub-100ms API response latency for dashboard updates, and robust memory management supporting large dataset uploads.

---

### 🔄 Slide 11: Compliance Investigator User Flow
*   **Visual**: Step-by-step UI mock flow showing the transition from alert queue to filing.
*   **Slide Header**: **Alert Triage & Investigation Lifecycle**
*   **Key Points**:
    *   **Step 1: Dataset Registry Switcher**: Select from global datasets (e.g., PaySim Benchmark vs uploaded logs).
    *   **Step 2: Alert Queue & Filtering**: Filter by risk tier, status, or search specific accounts.
    *   **Step 3: Interactive Deep Dive**: View interactive Network Graphs and SHAP explainability cards.
    *   **Step 4: Feedback Loop & SAR**: Submit investigator feedback (Confirm Mule, False Positive) which updates the DB, and auto-generate Suspicious Activity Reports (SAR).

---

### 🎯 Slide 12: Business Impact & Technical Roadmap
*   **Visual**: Side-by-side comparison panel mapping business metrics against upcoming roadmap modules.
*   **Slide Header**: **Business Impact & Platform Future Scope**
*   **Key Points**:
    *   **Business Impact**:
        *   🎯 **40% reduction** in false positive alert rates compared to traditional rule thresholds.
        *   ⏱️ **Alert Triage Time Reduced**: Investigation speed increases by up to 5x using inline graphs and SHAP explanations.
    *   **Technical Roadmap**:
        *   ⚡ *Streaming Graph Architecture*: Transition from batch execution to real-time graph updates using Apache Kafka.
        *   🕸️ *Graph Neural Networks (GNN)*: Train GraphSAGE models to automatically learn structural graph representations of transaction entities.
