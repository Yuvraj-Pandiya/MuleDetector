"""
app/services/features_graph.py
--------------------------------
Extended Graph Feature & Network Topology Engine using NetworkX + Scipy.

Node = account_id
Directed Edge = transaction from sender to receiver

Calculates account-level graph features:
  - In-degree, out-degree, total-degree, fan-in ratio, fan-out ratio
  - Unique in/out counterparties
  - Transaction-weighted in/out degree (monetary volume)
  - Short-cycle indicator & cycle count (via sparse matrix powers A^k)
  - PageRank & configurable pivot-sampled Betweenness Centrality
  - Local clustering coefficient (cohesion)

Also provides topology analysis:
  - Overall graph statistics
  - Top-risk structural nodes
  - Suspiciously dense connected components (mule ring candidates)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Tuple

import networkx as nx
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

logger = logging.getLogger(__name__)

_EPS = 1e-9

# Scalability Thresholds
LARGE_GRAPH_THRESHOLD = 5_000
BETWEENNESS_K_SAMPLE = 500

EXTENDED_GRAPH_COLUMNS: list[str] = [
    "in_degree",
    "out_degree",
    "total_degree",
    "fan_in_ratio",
    "fan_out_ratio",
    "unique_in_counterparties",
    "unique_out_counterparties",
    "transaction_weighted_in_degree",
    "transaction_weighted_out_degree",
    "is_in_short_cycle",
    "short_cycle_indicator",
    "cycle_count",
    "pagerank",
    "betweenness_centrality",
    "clustering_coefficient",
]

# Standard schema contract columns
GRAPH_COLUMNS: list[str] = [
    "in_degree",
    "out_degree",
    "is_in_short_cycle",
    "betweenness_centrality",
    "fan_in_ratio",
    "fan_out_ratio",
    "total_degree",
    "unique_in_counterparties",
    "unique_out_counterparties",
    "transaction_weighted_in_degree",
    "transaction_weighted_out_degree",
    "short_cycle_indicator",
    "cycle_count",
    "pagerank",
    "clustering_coefficient",
]


def _build_weighted_graph(df: pd.DataFrame) -> Tuple[nx.DiGraph, List[str]]:
    """Build directed weighted graph from transaction DataFrame."""
    G = nx.DiGraph()

    # Aggregate weighted edge amounts between (sender, receiver)
    edge_summary = (
        df.groupby(["sender_account_id", "receiver_account_id"])
        .agg(weight=("amount", "sum"), count=("amount", "count"))
        .reset_index()
    )

    for _, row in edge_summary.iterrows():
        G.add_edge(
            str(row["sender_account_id"]),
            str(row["receiver_account_id"]),
            weight=float(row["weight"]),
            count=int(row["count"]),
        )

    all_accounts = set(df["sender_account_id"].astype(str)) | set(df["receiver_account_id"].astype(str))
    G.add_nodes_from(all_accounts)

    return G, sorted(list(G.nodes()))


def _short_cycle_analysis(G: nx.DiGraph, nodes: List[str]) -> Tuple[Dict[str, int], Dict[str, int]]:
    """
    Compute short-cycle indicator (length <= 4) and total cycle hit count per node
    using sparse adjacency matrix powers A^k.
    """
    n = len(nodes)
    if n == 0:
        return {}, {}

    node_idx = {node: i for i, node in enumerate(nodes)}

    rows, cols = [], []
    for u, v in G.edges():
        if u in node_idx and v in node_idx:
            rows.append(node_idx[u])
            cols.append(node_idx[v])

    data = np.ones(len(rows), dtype=np.float32)
    A = csr_matrix((data, (rows, cols)), shape=(n, n))

    cycle_indicator = np.zeros(n, dtype=int)
    cycle_counts = np.zeros(n, dtype=int)

    Ak = A
    for k in range(2, 5):  # k = 2, 3, 4 hops
        Ak = Ak.dot(A) if k > 2 else A.dot(A)
        diag = np.array(Ak.diagonal()).flatten()
        cycle_indicator = np.maximum(cycle_indicator, (diag > 0).astype(int))
        cycle_counts += diag.astype(int)

    flag_map = {node: int(cycle_indicator[node_idx[node]]) for node in nodes}
    count_map = {node: int(cycle_counts[node_idx[node]]) for node in nodes}
    return flag_map, count_map


def compute_graph_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute scalable graph features per account.
    """
    if df.empty:
        return pd.DataFrame(columns=["account_id"] + EXTENDED_GRAPH_COLUMNS)

    df = df.copy()
    G, nodes = _build_weighted_graph(df)
    n_nodes = len(nodes)

    logger.info("[GraphFeatures] Built graph: %d nodes, %d directed edges", n_nodes, G.number_of_edges())

    # Degrees & Weighted Degrees
    in_deg = dict(G.in_degree())
    out_deg = dict(G.out_degree())

    weighted_in_deg = dict(G.in_degree(weight="weight"))
    weighted_out_deg = dict(G.out_degree(weight="weight"))

    # Short Cycle Analysis (Sparse Matrix Powers)
    cycle_flags, cycle_counts = _short_cycle_analysis(G, nodes)

    # PageRank
    try:
        pr = nx.pagerank(G, alpha=0.85, max_iter=100)
    except Exception as exc:
        logger.warning("[GraphFeatures] PageRank convergence issue (%s) — falling back to uniform", exc)
        pr = {node: 1.0 / max(n_nodes, 1) for node in nodes}

    # Betweenness Centrality (Pivot Sampling for Large Graphs)
    if n_nodes > LARGE_GRAPH_THRESHOLD:
        k_sample = min(BETWEENNESS_K_SAMPLE, n_nodes)
        logger.info("[GraphFeatures] Large graph (%d nodes): pivot sampling k=%d for betweenness", n_nodes, k_sample)
        bc = nx.betweenness_centrality(G, k=k_sample, normalized=True, seed=42)
    else:
        bc = nx.betweenness_centrality(G, normalized=True)

    # Clustering Coefficient (Directed Cohesion)
    try:
        clustering = nx.clustering(G)
    except Exception:
        clustering = {node: 0.0 for node in nodes}

    records = []
    for node in nodes:
        ind = in_deg.get(node, 0)
        outd = out_deg.get(node, 0)
        totd = ind + outd
        denom = totd + _EPS

        records.append({
            "account_id": node,
            "in_degree": ind,
            "out_degree": outd,
            "total_degree": totd,
            "fan_in_ratio": round(ind / denom, 4),
            "fan_out_ratio": round(outd / denom, 4),
            "unique_in_counterparties": ind,
            "unique_out_counterparties": outd,
            "transaction_weighted_in_degree": round(float(weighted_in_deg.get(node, 0.0)), 2),
            "transaction_weighted_out_degree": round(float(weighted_out_deg.get(node, 0.0)), 2),
            "is_in_short_cycle": cycle_flags.get(node, 0),
            "short_cycle_indicator": cycle_flags.get(node, 0),
            "cycle_count": cycle_counts.get(node, 0),
            "pagerank": round(float(pr.get(node, 0.0)), 6),
            "betweenness_centrality": round(float(bc.get(node, 0.0)), 6),
            "clustering_coefficient": round(float(clustering.get(node, 0.0)), 4),
        })

    result_df = pd.DataFrame(records)
    out_cols = ["account_id"] + [c for c in EXTENDED_GRAPH_COLUMNS if c in result_df.columns]
    return result_df[out_cols]


def analyze_graph_topology(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze network graph topology and return:
      - graph_statistics
      - top_risk_nodes
      - suspicious_connected_components (dense mule ring subgraphs)
    """
    G, nodes = _build_weighted_graph(df)
    n_nodes = len(nodes)
    n_edges = G.number_of_edges()

    if n_nodes == 0:
        return {"graph_statistics": {}, "top_risk_nodes": [], "suspicious_connected_components": []}

    # Graph Statistics
    density = nx.density(G)
    wcc = list(nx.weakly_connected_components(G))
    scc = list(nx.strongly_connected_components(G))

    in_deg = dict(G.in_degree())
    out_deg = dict(G.out_degree())

    graph_stats = {
        "node_count": n_nodes,
        "edge_count": n_edges,
        "density": round(density, 6),
        "weakly_connected_components_count": len(wcc),
        "strongly_connected_components_count": len(scc),
        "max_in_degree": max(in_deg.values()) if in_deg else 0,
        "max_out_degree": max(out_deg.values()) if out_deg else 0,
    }

    # Node Centrality & Risk Ranking
    features_df = compute_graph_features(df)
    top_nodes = (
        features_df.sort_values(
            by=["is_in_short_cycle", "betweenness_centrality", "pagerank"],
            ascending=[False, False, False],
        )
        .head(10)[["account_id", "total_degree", "is_in_short_cycle", "betweenness_centrality", "pagerank"]]
        .to_dict(orient="records")
    )

    # Detect Suspiciously Dense Connected Components (Mule Ring Candidates)
    suspicious_components = []
    cycle_flags, _ = _short_cycle_analysis(G, nodes)

    for idx, comp_nodes in enumerate(wcc):
        if len(comp_nodes) >= 3:  # Focus on subgraphs with >= 3 accounts
            subG = G.subgraph(comp_nodes)
            sub_nodes = len(subG)
            sub_edges = subG.number_of_edges()
            sub_density = sub_edges / max(sub_nodes * (sub_nodes - 1), 1)

            sub_cycle_hits = sum(cycle_flags.get(n, 0) for n in comp_nodes)
            sub_cycle_ratio = sub_cycle_hits / max(sub_nodes, 1)

            # Flag as suspicious if density > 0.15 OR cycle_ratio > 0.30
            if sub_density >= 0.15 or sub_cycle_ratio >= 0.30:
                suspicious_components.append({
                    "component_id": f"RING_{idx+1:03d}",
                    "node_count": sub_nodes,
                    "edge_count": sub_edges,
                    "density": round(sub_density, 4),
                    "cycle_involvement_ratio": round(sub_cycle_ratio, 4),
                    "nodes": list(comp_nodes)[:20],  # Sample first 20 nodes
                    "risk_flag": "HIGH_NETWORK_DENSITY_MULE_RING",
                })

    return {
        "graph_statistics": graph_stats,
        "top_risk_nodes": top_nodes,
        "suspicious_connected_components": suspicious_components,
    }
