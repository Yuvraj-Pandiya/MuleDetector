"""
tests/test_realtime_pipeline.py
================================
Unit test suite for the real-time transaction scoring pipeline,
validation rules, 8-stage flow, structured telemetry logging, and
AbstractEventConsumer interface for Kafka decoupling.
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import pytest

from app.services.realtime_pipeline import (
    AbstractEventConsumer,
    LocalStreamConsumer,
    TransactionValidationError,
    process_realtime_transaction,
    validate_transaction,
)


def test_validate_transaction_valid():
    valid_payload = {
        "transaction_id": "TXN-1001",
        "sender_id": "ACC-001005",
        "receiver_id": "ACC-002012",
        "amount": 1500.0,
    }
    # Should not raise any error
    validate_transaction(valid_payload)


def test_validate_transaction_missing_fields():
    invalid_payload = {
        "sender_id": "ACC-001005",
        "amount": 1500.0,
    }
    with pytest.raises(TransactionValidationError, match="Missing required transaction fields"):
        validate_transaction(invalid_payload)


def test_validate_transaction_negative_amount():
    invalid_payload = {
        "transaction_id": "TXN-1002",
        "sender_id": "ACC-001005",
        "receiver_id": "ACC-002012",
        "amount": -50.0,
    }
    with pytest.raises(TransactionValidationError, match="must be strictly positive"):
        validate_transaction(invalid_payload)


def test_validate_transaction_self_transfer():
    invalid_payload = {
        "transaction_id": "TXN-1003",
        "sender_id": "ACC-001005",
        "receiver_id": "ACC-001005",
        "amount": 500.0,
    }
    with pytest.raises(TransactionValidationError, match="Self-transactions"):
        validate_transaction(invalid_payload)


def test_process_realtime_transaction_flow():
    payload = {
        "transaction_id": "TXN-TEST-88",
        "sender_id": "ACC-TEST-SENDER",
        "receiver_id": "ACC-TEST-RECEIVER",
        "amount": 45000.0,
    }

    result = process_realtime_transaction(payload)

    assert result["transaction_id"] == "TXN-TEST-88"
    assert "prediction_time" in result
    assert "model_version" in result
    assert "risk_score" in result
    assert "latency_ms" in result
    assert isinstance(result["alert_created"], bool)
    assert result["risk_score"] >= 0.0 and result["risk_score"] <= 100.0


def test_local_stream_consumer_decoupling():
    consumer = LocalStreamConsumer()
    assert isinstance(consumer, AbstractEventConsumer)

    payload = {
        "transaction_id": "TXN-CONSUMER-1",
        "sender_id": "ACC-S1",
        "receiver_id": "ACC-R1",
        "amount": 120.0,
    }

    result = consumer.consume_event(payload)
    assert result["transaction_id"] == "TXN-CONSUMER-1"
    assert "risk_score" in result
