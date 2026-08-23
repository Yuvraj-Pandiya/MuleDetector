# ⚡ MuleScope Hackathon Pitch Guide (README Format)

This document contains a high-impact, structured pitch script, demo walkthrough, and Q&A survival guide for presenting **MuleScope** at your hackathon demo. Use this to hook the judges, explain your tech stack clearly, and nail the business impact in under 3 minutes.

---

## 🎤 The 3-Minute Hackathon Pitch Script

### ⏱️ Phase 1: The Hook & The Problem (0:00 - 0:45)
> **"Judges, every single year, over $2 Trillion is laundered globally, and the majority of it passes through 'Money Mules'—legitimate-looking accounts hijacked or rented by fraud syndicates. Legacy anti-money laundering systems are failing. Why? Because they rely on static rules, like flagging any transfer over ₹2,00,000. Fraudsters bypass this easily by dividing transfers into smaller amounts, running funds through complex network loops, and emptying accounts within minutes."**

### ⚙️ Phase 2: Introducing MuleScope (0:45 - 1:30)
> **"To stop this, we built MuleScope—an autonomous, multi-signal AI/ML platform that moves from isolated transaction alerts to network-aware money laundering ring detection."**
> 
> **"Our core tech consists of a three-signal decision engine:**
> 1. **Supervised XGBoost** trained on 74 behavioral, velocity, and fund-flow features to identify known fraud profiles.
> 2. **Unsupervised Isolation Forest** acting as a zero-day sensor to catch brand new, unseen anomalies.
> 3. **Graph Topology Algorithms** that evaluate PageRank, centrality, and run adjacency matrix powers to detect multi-hop transaction loops (e.g., A ➔ B ➔ C ➔ A) in milliseconds."

### 🖥️ Phase 3: The Live Demo Walkthrough (1:30 - 2:30)
> **"Let us show you how a compliance officer triages alerts in real-time on our dashboard:"**
> * **Named Dataset Switcher**: *"We can switch datasets instantly—from our baseline PaySim synthetic dataset of 15,420 accounts to a newly uploaded 191-account bank transfer log. The entire UI reactively re-evaluates all ML metrics in real-time."*
> * **Interactive Network Topology Graph**: *"Here, we visualize the counterparty flow. You can see dense mule rings and transaction loops flagged in red. Nodes are sized by PageRank and colored by risk tier."*
> * **Explainable AI (XAI)**: *"Compliance officers hate black-box AI. In our Explainability view, we use SHAP values to explain the model's decision in plain English: 'Flagged because 94% of inbound volume was transferred out within 5 minutes, and account is part of a 3-hop loop'."*
> * **HITL Loop**: *"The officer can confirm a mule account, instantly updating our database and automatically generating a download-ready Suspicious Activity Report (SAR) draft."*

### 🎯 Phase 4: Business Value & The Wrap (2:30 - 3:00)
> **"MuleScope reduces false-positive alerts by up to 40% compared to legacy rule engines, saving compliance teams thousands of hours. The platform runs on a FastAPI backend deployed on Render, and a glassmorphism React console on Vercel."**
> 
> **"With MuleScope, we are turning transaction monitoring into an autonomous, explainable graph network. Thank you, we are now open for questions!"**

---

## 🛠️ The Tech Stack (Under the Hood)
| Layer | Tech / Tool | Function |
|---|---|---|
| **Frontend** | React, Vite, Lucide icons, Recharts, `react-force-graph-2d` | Responsive compliance dashboard with high-fidelity glassmorphism themes. |
| **Backend** | FastAPI, Python 3.12, Uvicorn | High-performance async REST API providing sub-100ms response times. |
| **ML Engine** | `scikit-learn` (IsolationForest), `xgboost` (XGBClassifier) | Dual-Signal Hybrid scoring model with target weighting. |
| **Graph Logic** | `NetworkX` | Adjacency matrix cycle math ($\text{diag}(A^2 + A^3 + A^4)$) & centralities. |
| **Database** | SQLite (WAL mode enabled) | Persistent registries for `datasets`, `alerts`, `feedback`, and `sar`. |

---

## 🛡️ Hackathon Q&A Survival Guide (What Judges Will Ask)

### Q1: "How do you handle the massive class imbalance in fraud data?"
* **Answer**: *"Money laundering is rare—in our benchmark dataset, the fraud rate is only **0.0466%** (a 2144:1 imbalance). To handle this without overfitting, we tuned the `scale_pos_weight` parameter in our supervised XGBoost model to penalize false negatives heavily. We also incorporated the unsupervised Isolation Forest model, which detects anomalies based on distance in the feature space without needing labels."*

### Q2: "How scalable is your graph cycle detection?"
* **Answer**: *"Calculating cycle paths on huge graphs is computationally expensive. We optimized this by utilizing sparse adjacency matrix powers ($\text{diag}(A^2 + A^3 + A^4)$) to detect multi-hop feedback loops in linear time (sub-second execution), and we limit path searches to local subgraphs around flagged hub accounts."*

### Q3: "What happens if a user refreshes the page? Is the active dataset lost?"
* **Answer**: *"No. We implemented a dual-layer persistence state: the chosen active dataset ID is saved in the browser's `localStorage` (surviving refreshes), and it synchronizes with our backend database on load so that all views (Graph, Alerts, Metrics, Dashboard) remain in sync."*

### Q4: "How does this scale to real-time transaction streaming?"
* **Answer**: *"Our feature engineering layer is designed around relative offsets (`as_of_timestamp` thresholds) rather than static date filters. This makes it highly compatible with streaming architectures like Apache Kafka or Apache Flink, where features can be calculated in slide windows as events arrive."*
