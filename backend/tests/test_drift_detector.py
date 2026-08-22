"""
tests/test_drift_detector.py
=============================
Unit test suite for model/feature drift detector, PSI calculations,
class-rate shift monitoring, and automated drift alerts.
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import numpy as np
import pytest

from app.services.drift_detector import calculate_psi, compute_drift_metrics


def test_calculate_psi_identical_distributions():
    expected = np.random.normal(10, 2, 1000)
    actual = np.random.normal(10, 2, 1000)
    psi = calculate_psi(expected, actual)
    assert psi < 0.10, f"Expected low PSI for identical distributions, got {psi}"


def test_calculate_psi_shifted_distributions():
    expected = np.random.normal(10, 2, 1000)
    actual = np.random.normal(25, 5, 1000)
    psi = calculate_psi(expected, actual)
    assert psi >= 0.25, f"Expected high PSI for shifted distributions, got {psi}"


def test_compute_drift_metrics_structure():
    report = compute_drift_metrics(warning_threshold=0.10, critical_threshold=0.25)

    assert "feature_drift_status" in report
    assert "drift_severity" in report
    assert "overall_psi" in report
    assert "prediction_distribution" in report
    assert "class_rate_shift" in report
    assert "monitored_features" in report

    for f_item in report["monitored_features"]:
        assert "feature" in f_item
        assert "drift_metric" in f_item
        assert f_item["status"] in ["NORMAL", "WARNING", "CRITICAL"]


def test_drift_alert_generation():
    # Force low thresholds to guarantee alert generation
    report = compute_drift_metrics(warning_threshold=0.001, critical_threshold=0.005)
    assert report["drift_alert_triggered"] is True
    assert report["drift_alert_details"] is not None
