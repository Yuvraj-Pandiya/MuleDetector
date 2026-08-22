"""
tests/test_candidate_trainer.py
================================
Unit test suite for Human-in-the-Loop (HITL) feedback collection,
label validation, candidate dataset creation, candidate retraining, model comparison,
and controlled model promotion.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import pytest

from app.services.candidate_trainer import (
    CANDIDATE_METRICS_PATH,
    CANDIDATE_MODEL_PATH,
    compare_candidate_vs_production,
    get_feedback_summary,
    promote_candidate_model,
    train_candidate_model,
    validate_and_build_candidate_dataset,
)
from app.services.feedback_store import submit_feedback


@pytest.fixture(autouse=True)
def setup_sample_feedback():
    """Submit sample feedback records before running tests."""
    submit_feedback("ALT-101", "ACC-001001", "CONFIRMED_MULE", "Confirmed mule ring participation", "Analyst #1")
    submit_feedback("ALT-102", "ACC-001002", "LEGITIMATE", "Verified legitimate payroll account", "Analyst #2")
    submit_feedback("ALT-103", "ACC-001003", "FALSE_POSITIVE", "False alarm on high transfer size", "Analyst #3")
    submit_feedback("ALT-104", "ACC-001004", "UNDER_INVESTIGATION", "Case pending investigation", "Analyst #4")


def test_feedback_summary():
    summary = get_feedback_summary()
    assert summary["total_feedback_entries"] >= 4
    assert summary["decision_counts"]["CONFIRMED_MULE"] >= 1
    assert summary["decision_counts"]["LEGITIMATE"] >= 1
    assert summary["decision_counts"]["FALSE_POSITIVE"] >= 1
    assert summary["validated_label_summary"]["positive_labels_mule"] >= 1
    assert summary["validated_label_summary"]["negative_labels_legit"] >= 2


def test_validate_and_build_candidate_dataset():
    df_candidate, meta = validate_and_build_candidate_dataset()
    assert not df_candidate.empty
    assert "is_mule_pattern" in df_candidate.columns
    assert meta["total_rows"] > 0


def test_train_candidate_model():
    metrics = train_candidate_model()
    assert CANDIDATE_MODEL_PATH.exists()
    assert CANDIDATE_METRICS_PATH.exists()

    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1" in metrics
    assert "pr_auc" in metrics
    assert metrics["model_version"].startswith("v2.6.0-HITL")


def test_compare_candidate_vs_production():
    comp = compare_candidate_vs_production()
    assert "production_model" in comp
    assert "candidate_model" in comp
    assert "metric_deltas" in comp
    assert comp["recommendation"] in ["RECOMMEND_PROMOTION", "REJECT_PROMOTION"]


def test_promote_candidate_model():
    promoted = promote_candidate_model()
    assert promoted["status"] == "promoted"
    assert "new_production_version" in promoted
    assert promoted["new_production_version"].startswith("v2.6.0-HITL-Promoted")
