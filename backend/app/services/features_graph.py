"""
app/services/features_graph.py
--------------------------------
Graph-based feature computation using NetworkX.

Builds a directed transaction graph (nodes = accounts, edges = transfers)
and computes per-account structural features.

Output columns (exactly as per docs/feature_schema.md):
  in_degree, out_degree, is_in_short_cycle,
  betweenness_centrality, fan_in_ratio, fan_out_ratio

Short-cycle detection strategy
-------------------------------
We want to flag accounts that participate in a directed cycle of length ≤ 4.
The exact formula uses sparse matrix self-loops:

    A^k[i, i] > 0  ⟹  node i is in a cycle of length k

We sum diagonals of A¹ + A² + A³ + A⁴ using scipy sparse arithmetic, which
is both exact and fast (< 1 s for 10k-node graphs).

Betweenness centrality
-----------------------
Exact computation is O(VE), which is prohibitive for large graphs.
We use k-sampled approximation (k=500 pivot nodes) whenever |V| > 5000.
"""
from __future__ import annotations

import time
from typing import Union

import networkx as nx
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

_EPS = 1e-9

GRAPH_COLUMNS: list[str] = [
    "in_degree",
    "out_degree",
    "is_in_short_cycle",
    "betweenness_centrality",
    "fan_in_ratio",
    "fan_out_ratio",
]

# Pivot count for approximate betweenness when |V| > LARGE_GRAPH_THRESHOLD
LARGE_GRAPH_THRESHOLD = 5_000
BETWEENNESS_K_SAMPLE   = 500


def _build_graph(df: pd.DataFrame) -> tuple[nx.DiGraph, list[str]]:
    """
    Build a directed graph from the transaction DataFrame.
    Returns (G, ordered_node_list).
    Multi-edges are collapsed to a single edge (we care about structure).
    """
    G = nx.DiGraph()
    edges = (
        df[["sender_account_id", "receiver_account_id"]]
        .drop_duplicates()
        .values.tolist()
    )
    G.add_edges_from(edges)

    # Make sure every account that only appears on one side is still a node
    all_accounts = set(df["sender_account_id"]) | set(df["receiver_account_id"])
    G.add_nodes_from(all_accounts)

    return G, list(G.nodes())


def _short_cycle_flags(G: nx.DiGraph, nodes: list[str]) -> dict[str, int]:
    """
    Return a dict {node: 1/0} indicating whether the node is in a directed
    cycle of length ≤ 4.

    Method: sparse adjacency matrix powers.
        node i is in a k-cycle  ⟺  (A^k)[i,i] > 0

    We check k ∈ {2, 3, 4}  (k=1 means a self-loop, which we skip for
    financial graphs).
    """
    n = len(nodes)
    if n == 0:
        return {}

    node_idx = {node: i for i, node in enumerate(nodes)}

    # Build sparse adjacency matrix
    rows, cols = [], []
    for u, v in G.edges():
        if u in node_idx and v in node_idx:
            rows.append(node_idx[u])
            cols.append(node_idx[v])

    data = np.ones(len(rows), dtype=np.float32)
    A = csr_matrix((data, (rows, cols)), shape=(n, n))

    # Accumulate diagonal hits across A², A³, A⁴
    in_cycle = np.zeros(n, dtype=bool)

    Ak = A
    for k in range(2, 5):           # k = 2, 3, 4
        Ak = Ak.dot(A) if k > 2 else A.dot(A)  # A^k
        diag = np.array(Ak.diagonal())
        in_cycle |= (diag > 0)

    return {node: int(in_cycle[node_idx[node]]) for node in nodes}


def compute_graph_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute graph-based structural features per account.

    Parameters
    ----------
    df : pd.DataFrame
        Transaction DataFrame with at least:
        sender_account_id, receiver_account_id.

    Returns
    -------
    pd.DataFrame
        Columns: ``account_id`` + GRAPH_COLUMNS.
        Types: in_degree, out_degree, is_in_short_cycle → int
               betweenness_centrality, fan_in_ratio, fan_out_ratio → float
    """
    t0 = time.perf_counter()

    df = df.copy()

    # ------------------------------------------------------------------
    # 1. Build directed graph
    # ------------------------------------------------------------------
    G, nodes = _build_graph(df)
    n_nodes = len(nodes)
    n_edges = G.number_of_edges()
    print(f"[graph] Graph built: {n_nodes:,} nodes, {n_edges:,} edges")

    # ------------------------------------------------------------------
    # 2. In-degree / out-degree (unique predecessors / successors)
    # ------------------------------------------------------------------
    in_deg  = dict(G.in_degree())
    out_deg = dict(G.out_degree())

    # ------------------------------------------------------------------
    # 3. Short-cycle detection (≤ 4 hops via sparse matrix powers)
    # ------------------------------------------------------------------
    t_cycle = time.perf_counter()
    cycle_flags = _short_cycle_flags(G, nodes)
    print(f"[graph] Short-cycle detection: {time.perf_counter() - t_cycle:.2f}s")

    # ------------------------------------------------------------------
    # 4. Betweenness centrality (k-sampled if graph is large)
    # ------------------------------------------------------------------
    t_bc = time.perf_counter()
    if n_nodes > LARGE_GRAPH_THRESHOLD:
        k = min(BETWEENNESS_K_SAMPLE, n_nodes)
        print(f"[graph] Large graph ({n_nodes} nodes): sampling k={k} for betweenness")
        bc = nx.betweenness_centrality(G, k=k, normalized=True, seed=42)
    else:
        bc = nx.betweenness_centrality(G, normalized=True)
    print(f"[graph] Betweenness centrality: {time.perf_counter() - t_bc:.2f}s")

    # ------------------------------------------------------------------
    # 5. Fan-in / fan-out ratios
    # ------------------------------------------------------------------
    records = []
    for node in nodes:
        ind  = in_deg.get(node, 0)
        outd = out_deg.get(node, 0)
        denom = ind + outd + _EPS
        records.append(
            {
                "account_id":             node,
                "in_degree":              ind,
                "out_degree":             outd,
                "is_in_short_cycle":      cycle_flags.get(node, 0),
                "betweenness_centrality": bc.get(node, 0.0),
                "fan_in_ratio":           ind  / denom,
                "fan_out_ratio":          outd / denom,
            }
        )

    result = pd.DataFrame(records)

    # ------------------------------------------------------------------
    # Type enforcement per schema contract
    # ------------------------------------------------------------------
    int_cols   = ["in_degree", "out_degree", "is_in_short_cycle"]
    float_cols = ["betweenness_centrality", "fan_in_ratio", "fan_out_ratio"]
    result[int_cols]   = result[int_cols].fillna(0).astype(int)
    result[float_cols] = result[float_cols].fillna(0.0).astype(float)

    elapsed = time.perf_counter() - t0
    print(f"[graph] Total time: {elapsed:.2f}s")

    return result[["account_id"] + GRAPH_COLUMNS]
