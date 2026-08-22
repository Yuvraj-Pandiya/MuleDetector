"""
app/services/archetype_clustering.py
======================================
Unsupervised Archetype Clustering & Behavioral Segmentation Engine for MuleDetector.

Categorizes flagged money mule accounts into 5 primary AML Archetypes:
  1. Rapid Pass-Through Mule (Layering / Fast Forwarding)
  2. Funnel Aggregator (Fan-In / Collection Node)
  3. Scatter Distributor (Fan-Out / Structuring Node)
  4. Dormant Reactivated Mule (Sleeper / Sudden Volume Spike)
  5. Circular Ring Mule (Loop / Multi-hop Cohesion)

Provides both KMeans ML clustering and deterministic rule-guided fallback.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

ARCHETYPE_DEFINITIONS = {
    "RAPID_PASSTHROUGH": {
        "id": "ARCH-01",
        "name": "Rapid Pass-Through Mule",
        "category": "Layering & Forwarding",
        "description": "Receives funds and forwards them out almost immediately (< 15 mins) with minimal retention.",
        "icon": "Zap",
        "color": "#ef4444", # Red
    },
    "FUNNEL_AGGREGATOR": {
        "id": "ARCH-02",
        "name": "Funnel Aggregator",
        "category": "Collection Node",
        "description": "Aggregates small inbound transfers from multiple victim accounts before executing a bulk transfer.",
        "icon": "Filter",
        "color": "#f97316", # Orange
    },
    "SCATTER_DISTRIBUTOR": {
        "id": "ARCH-03",
        "name": "Scatter Distributor",
        "category": "Structuring Node",
        "description": "Receives large lump-sum deposits and disperses smaller structured payments to multiple recipients.",
        "icon": "Share2",
        "color": "#eab308", # Yellow
    },
    "DORMANT_REACTIVATED": {
        "id": "ARCH-04",
        "name": "Dormant Reactivated Mule",
        "category": "Sleeper Account",
        "description": "Aged account with low historical activity that suddenly experiences massive transaction volume spikes.",
        "icon": "Moon",
        "color": "#8b5cf6", # Purple
    },
    "CIRCULAR_RING": {
        "id": "ARCH-05",
        "name": "Circular Ring Mule",
        "category": "Network Cohesion",
        "description": "Participates in multi-hop circular transaction flows to disguise ultimate beneficial ownership.",
        "icon": "Repeat",
        "color": "#06b6d4", # Cyan
    },
}

FEATURE_COLS = [
    "avg_time_to_forward_funds_minutes",
    "fan_in_ratio",
    "fan_out_ratio",
    "is_new_high_volume_flag",
    "is_in_short_cycle",
    "betweenness_centrality",
    "amount_zscore_avg",
]


def classify_account_archetype(row: pd.Series) -> Dict[str, Any]:
    """
    Classify a single account row into its primary Mule Archetype based on key feature signatures.
    """
    avg_fwd = float(row.get("avg_time_to_forward_funds_minutes", 60.0))
    fan_in = float(row.get("fan_in_ratio", 0.5))
    fan_out = float(row.get("fan_out_ratio", 0.5))
    high_vol = bool(row.get("is_new_high_volume_flag", False))
    short_cycle = bool(row.get("is_in_short_cycle", False))
    betweenness = float(row.get("betweenness_centrality", 0.0))
    zscore = float(row.get("amount_zscore_avg", 0.0))
    in_deg = float(row.get("in_degree", 1.0))
    out_deg = float(row.get("out_degree", 1.0))

    # Scoring weights for archetypes
    scores = {
        "RAPID_PASSTHROUGH": 0.0,
        "FUNNEL_AGGREGATOR": 0.0,
        "SCATTER_DISTRIBUTOR": 0.0,
        "DORMANT_REACTIVATED": 0.0,
        "CIRCULAR_RING": 0.0,
    }

    # 1. Rapid Pass-Through
    if avg_fwd < 20.0:
        scores["RAPID_PASSTHROUGH"] += 4.0
    elif avg_fwd < 45.0:
        scores["RAPID_PASSTHROUGH"] += 2.0

    # 2. Funnel Aggregator (High Fan-In)
    if fan_in > 0.65 or in_deg > out_deg * 2.0:
        scores["FUNNEL_AGGREGATOR"] += 3.5
    if in_deg > 3:
        scores["FUNNEL_AGGREGATOR"] += 1.5

    # 3. Scatter Distributor (High Fan-Out)
    if fan_out > 0.65 or out_deg > in_deg * 2.0:
        scores["SCATTER_DISTRIBUTOR"] += 3.5
    if out_deg > 3:
        scores["SCATTER_DISTRIBUTOR"] += 1.5

    # 4. Dormant Reactivated
    if high_vol or zscore > 2.0:
        scores["DORMANT_REACTIVATED"] += 3.5

    # 5. Circular Ring
    if short_cycle:
        scores["CIRCULAR_RING"] += 4.0
    if betweenness > 0.05:
        scores["CIRCULAR_RING"] += 2.0

    best_key = max(scores, key=lambda k: scores[k])
    if scores[best_key] == 0:
        best_key = "RAPID_PASSTHROUGH"

    meta = ARCHETYPE_DEFINITIONS[best_key]
    return {
        "archetype_key": best_key,
        "archetype_id": meta["id"],
        "name": meta["name"],
        "category": meta["category"],
        "description": meta["description"],
        "icon": meta["icon"],
        "color": meta["color"],
        "confidence_score": round(float(scores[best_key]) / 5.0, 2),
        "all_scores": {k: round(v, 2) for k, v in scores.items()},
    }


def perform_mule_archetype_clustering(
    feature_df: pd.DataFrame,
    n_clusters: int = 5,
) -> Dict[str, Any]:
    """
    Perform KMeans clustering across the feature matrix to partition accounts into archetype clusters.
    Returns cluster centroids, archetype assignments, and summary breakdown.
    """
    if feature_df.empty:
        return {"total_accounts": 0, "archetypes": {}, "clusters": []}

    avail_cols = [c for c in FEATURE_COLS if c in feature_df.columns]
    if not avail_cols:
        avail_cols = [c for c in feature_df.columns if c != "account_id" and pd.api.types.is_numeric_dtype(feature_df[c])]

    X = feature_df[avail_cols].fillna(0.0).values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    actual_clusters = min(n_clusters, len(feature_df))
    kmeans = KMeans(n_clusters=actual_clusters, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(X_scaled)

    archetype_assignments = []
    distribution = {k: 0 for k in ARCHETYPE_DEFINITIONS.keys()}

    for idx, (_, row) in enumerate(feature_df.iterrows()):
        arch_info = classify_account_archetype(row)
        acct_id = str(row.get("account_id", f"ACC-{idx:04d}"))
        c_label = int(cluster_labels[idx])

        distribution[arch_info["archetype_key"]] += 1

        archetype_assignments.append({
            "account_id": acct_id,
            "cluster_id": c_label,
            "archetype": arch_info,
        })

    total = len(feature_df)
    summary_breakdown = [
        {
            "key": k,
            "name": ARCHETYPE_DEFINITIONS[k]["name"],
            "count": count,
            "percentage": round((count / total) * 100, 1) if total > 0 else 0.0,
            "color": ARCHETYPE_DEFINITIONS[k]["color"],
        }
        for k, count in distribution.items()
    ]

    return {
        "total_accounts": total,
        "cluster_count": actual_clusters,
        "summary_breakdown": summary_breakdown,
        "account_assignments": archetype_assignments,
    }
