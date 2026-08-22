"""
tests/test_features_graph.py
==============================
Unit tests for the extended graph feature module and network topology engine.
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import pandas as pd
import pytest

from app.services.features_graph import (
    EXTENDED_GRAPH_COLUMNS,
    analyze_graph_topology,
    compute_graph_features,
)


@pytest.fixture
def graph_sample_txns() -> pd.DataFrame:
    """
    Create a directed cycle graph:
      ACC_A -> ACC_B (500.0)
      ACC_B -> ACC_C (450.0)
      ACC_C -> ACC_A (400.0)  (Cycle A-B-C)
      ACC_C -> ACC_D (1000.0)
    """
    txns = [
        {"sender_account_id": "ACC_A", "receiver_account_id": "ACC_B", "amount": 500.0},
        {"sender_account_id": "ACC_B", "receiver_account_id": "ACC_C", "amount": 450.0},
        {"sender_account_id": "ACC_C", "receiver_account_id": "ACC_A", "amount": 400.0},
        {"sender_account_id": "ACC_C", "receiver_account_id": "ACC_D", "amount": 1000.0},
    ]
    return pd.DataFrame(txns)


def test_degree_and_fan_ratios(graph_sample_txns: pd.DataFrame):
    """Test in_degree, out_degree, total_degree, fan_in_ratio, fan_out_ratio."""
    res = compute_graph_features(graph_sample_txns)
    row_c = res[res["account_id"] == "ACC_C"].iloc[0]

    # ACC_C has in_degree = 1 (from B) and out_degree = 2 (to A and D)
    assert row_c["in_degree"] == 1
    assert row_c["out_degree"] == 2
    assert row_c["total_degree"] == 3
    assert pytest.approx(row_c["fan_in_ratio"], 0.01) == 1/3
    assert pytest.approx(row_c["fan_out_ratio"], 0.01) == 2/3


def test_transaction_weighted_degrees(graph_sample_txns: pd.DataFrame):
    """Test transaction_weighted_in_degree and transaction_weighted_out_degree."""
    res = compute_graph_features(graph_sample_txns)
    row_c = res[res["account_id"] == "ACC_C"].iloc[0]

    # ACC_C weighted in = 450.0 (from B), weighted out = 400.0 + 1000.0 = 1400.0
    assert pytest.approx(row_c["transaction_weighted_in_degree"], 0.01) == 450.0
    assert pytest.approx(row_c["transaction_weighted_out_degree"], 0.01) == 1400.0


def test_short_cycle_detection(graph_sample_txns: pd.DataFrame):
    """Test short-cycle indicator and cycle count for 3-node cycle A-B-C."""
    res = compute_graph_features(graph_sample_txns)
    row_a = res[res["account_id"] == "ACC_A"].iloc[0]
    row_d = res[res["account_id"] == "ACC_D"].iloc[0]

    # ACC_A is part of cycle A->B->C->A
    assert row_a["is_in_short_cycle"] == 1
    assert row_a["short_cycle_indicator"] == 1
    assert row_a["cycle_count"] >= 1

    # ACC_D is a sink node (out_degree=0, no cycle)
    assert row_d["is_in_short_cycle"] == 0
    assert row_d["cycle_count"] == 0


def test_pagerank_and_centrality(graph_sample_txns: pd.DataFrame):
    """Test PageRank and Betweenness Centrality metrics."""
    res = compute_graph_features(graph_sample_txns)

    assert "pagerank" in res.columns
    assert "betweenness_centrality" in res.columns

    # PageRank & Betweenness should be non-negative
    assert (res["pagerank"] >= 0.0).all()
    assert (res["betweenness_centrality"] >= 0.0).all()


def test_topology_analysis(graph_sample_txns: pd.DataFrame):
    """Test analyze_graph_topology report and suspicious component detection."""
    analysis = analyze_graph_topology(graph_sample_txns)

    stats = analysis["graph_statistics"]
    assert stats["node_count"] == 4
    assert stats["edge_count"] == 4
    assert "density" in stats

    top_nodes = analysis["top_risk_nodes"]
    assert len(top_nodes) > 0

    susp_comp = analysis["suspicious_connected_components"]
    assert len(susp_comp) >= 1
    assert susp_comp[0]["node_count"] >= 3
