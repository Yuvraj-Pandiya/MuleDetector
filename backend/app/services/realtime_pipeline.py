"""
app/services/realtime_pipeline.py
==================================
Real-time Transaction Scoring Pipeline for MuleDetector.

Flow:
  Incoming transaction
  → 1. Validation
  → 2. Feature update (stateful sliding window telemetry)
  → 3. Account feature retrieval/update
  → 4. ML inference (Supervised XGBoost probability)
  → 5. Anomaly scoring (Isolation Forest score)
  → 6. Network risk lookup/update (Graph topology degree/centrality)
  → 7. Risk fusion (Calibrated composite risk score 0-100 & tier)
  → 8. Alert generation (Prioritized SQLite alert creation)

Log Format:
  transaction_id
  prediction_time
  model_version
  risk_score
  latency
  alert_created

Design:
  Uses AbstractEventConsumer so a future KafkaStreamConsumer can replace
  LocalStreamConsumer without modifying ML inference or feature processing logic.
  Coexists cleanly with existing batch pipeline.
"""

from __future__ import annotations

import abc
import datetime
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from app.services.alert_generator import create_alert
from app.services.risk_scorer import score_account_risk

logger = logging.getLogger(__name__)

# Structured Logger for Real-Time Transaction Scoring Audit
realtime_logger = logging.getLogger("mule_detector.realtime")


class TransactionValidationError(ValueError):
    """Raised when an incoming transaction event fails validation rules."""
    pass


class StatefulFeatureStore:
    """
    In-memory stateful feature store tracking sliding window transaction telemetry
    for real-time account feature calculation.
    """

    def __init__(self) -> None:
        self.account_history: Dict[str, List[Dict[str, Any]]] = {}

    def update_account_state(self, txn: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Record incoming transaction and compute updated account feature vectors
        for sender and receiver accounts.
        """
        sender_id = str(txn["sender_id"])
        receiver_id = str(txn["receiver_id"])
        amount = float(txn["amount"])
        timestamp_str = str(txn.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat()))

        # Parse timestamp
        try:
            ts_dt = datetime.datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except Exception:
            ts_dt = datetime.datetime.now(datetime.timezone.utc)

        ts_epoch = ts_dt.timestamp()

        # Add to history
        for acct_id, role in [(sender_id, "SENDER"), (receiver_id, "RECEIVER")]:
            if acct_id not in self.account_history:
                self.account_history[acct_id] = []
            self.account_history[acct_id].append({
                "txn_id": txn.get("transaction_id"),
                "role": role,
                "amount": amount,
                "timestamp_epoch": ts_epoch,
                "timestamp_dt": ts_dt,
                "counterparty": receiver_id if role == "SENDER" else sender_id,
            })

        # Compute sender feature vector
        sender_features = self._compute_feature_vector(sender_id, ts_epoch)
        receiver_features = self._compute_feature_vector(receiver_id, ts_epoch)

        return sender_features, receiver_features

    def _compute_feature_vector(self, account_id: str, current_epoch: float) -> Dict[str, Any]:
        """Compute rolling 1h / 24h feature metrics for a specific account."""
        history = self.account_history.get(account_id, [])

        h1_cutoff = current_epoch - 3600
        h24_cutoff = current_epoch - 86400

        txns_1h = [t for t in history if t["timestamp_epoch"] >= h1_cutoff]
        txns_24h = [t for t in history if t["timestamp_epoch"] >= h24_cutoff]

        sent_24h = sum(t["amount"] for t in txns_24h if t["role"] == "SENDER")
        recv_24h = sum(t["amount"] for t in txns_24h if t["role"] == "RECEIVER")

        ratio_recv_sent = recv_24h / max(sent_24h, 1.0) if sent_24h > 0 else (1.0 if recv_24h > 0 else 0.0)

        counterparties_24h = len(set(t["counterparty"] for t in txns_24h))

        amounts_24h = [t["amount"] for t in txns_24h]
        mean_amt = float(np.mean(amounts_24h)) if amounts_24h else 0.0
        std_amt = float(np.std(amounts_24h)) if len(amounts_24h) > 1 else 1.0
        zscore_amt = (history[-1]["amount"] - mean_amt) / max(std_amt, 1.0) if history else 0.0

        # Calculate pass-through fund forwarding speed (minutes)
        recv_times = [t["timestamp_epoch"] for t in txns_24h if t["role"] == "RECEIVER"]
        sent_times = [t["timestamp_epoch"] for t in txns_24h if t["role"] == "SENDER"]

        forward_latencies = []
        for st in sent_times:
            prior_recvs = [rt for rt in recv_times if rt <= st]
            if prior_recvs:
                latency_min = (st - max(prior_recvs)) / 60.0
                forward_latencies.append(latency_min)

        avg_forward_min = float(np.mean(forward_latencies)) if forward_latencies else 15.0

        return {
            "account_id": account_id,
            "txn_count_1h": len(txns_1h),
            "txn_count_24h": len(txns_24h),
            "velocity": len(txns_1h) * 1.5,
            "unique_counterparty_count": counterparties_24h,
            "amount_zscore_avg": round(zscore_amt, 3),
            "ratio_received_to_sent_24h": round(ratio_recv_sent, 3),
            "avg_time_to_forward_funds_minutes": round(avg_forward_min, 2),
            "odd_hour_txn_ratio": 0.12 if history and history[-1]["timestamp_dt"].hour in (0, 1, 2, 3, 4, 5) else 0.02,
        }


# Global singleton feature store instance
_FEATURE_STORE = StatefulFeatureStore()


def validate_transaction(txn: Dict[str, Any]) -> None:
    """
    Stage 1: Validate transaction schema, non-negative amounts, and required fields.
    """
    if not isinstance(txn, dict):
        raise TransactionValidationError("Transaction payload must be a JSON dictionary.")

    required_fields = ["transaction_id", "sender_id", "receiver_id", "amount"]
    missing = [f for f in required_fields if f not in txn or txn[f] is None]
    if missing:
        raise TransactionValidationError(f"Missing required transaction fields: {missing}")

    sender_id = str(txn["sender_id"]).strip()
    receiver_id = str(txn["receiver_id"]).strip()
    if not sender_id or not receiver_id:
        raise TransactionValidationError("sender_id and receiver_id must not be empty.")

    if sender_id == receiver_id:
        raise TransactionValidationError("Self-transactions (sender_id == receiver_id) are invalid.")

    try:
        amount = float(txn["amount"])
    except (ValueError, TypeError):
        raise TransactionValidationError(f"Invalid transaction amount: {txn['amount']}")

    if amount <= 0:
        raise TransactionValidationError(f"Transaction amount must be strictly positive (> 0), got: {amount}")


def process_realtime_transaction(txn: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the full 8-stage real-time transaction scoring flow:
      1. Validation
      2. Feature update
      3. Account feature retrieval/update
      4. ML inference (Supervised probability)
      5. Anomaly scoring (Isolation Forest)
      6. Network risk lookup/update
      7. Risk fusion (Calibrated risk score 0-100)
      8. Alert generation

    Returns structured scoring response and logs JSON audit telemetry.
    """
    t0 = time.perf_counter()
    pred_time_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # --- Stage 1: Validation ---
    validate_transaction(txn)

    txn_id = str(txn["transaction_id"])
    sender_id = str(txn["sender_id"])
    receiver_id = str(txn["receiver_id"])
    amount = float(txn["amount"])

    # --- Stage 2 & 3: Feature Update & Retrieval ---
    sender_features, receiver_features = _FEATURE_STORE.update_account_state(txn)

    # --- Stage 4, 5, 6, 7: ML Inference, Anomaly Scoring, Network Lookup & Risk Fusion ---
    # Wrap sender features in DataFrame for risk scorer engine
    df_sender = pd.DataFrame([sender_features])
    
    # Calculate calibrated fused risk score
    risk_result = score_account_risk(sender_features, model_version="v2.5.0-RealTime-XGB")

    risk_score = float(risk_result.get("risk_score", 50.0))
    risk_tier = str(risk_result.get("risk_tier", "MEDIUM"))
    supervised_prob = float(risk_result.get("supervised_probability", 0.50))
    anomaly_score = float(risk_result.get("anomaly_score", 0.35))
    network_risk = float(risk_result.get("network_risk_score", 40.0))
    model_version = str(risk_result.get("model_version", "v2.5.0-RealTime-XGB"))

    # --- Stage 8: Alert Generation ---
    alert_created = False
    alert_id = None

    if risk_score >= 60.0 or risk_tier in ("CRITICAL", "HIGH"):
        top_reasons = risk_result.get("top_reasons", [
            f"Elevated velocity burst ({sender_features.get('txn_count_1h', 1)} txns/hr)",
            f"Rapid fund forwarding latency ({sender_features.get('avg_time_to_forward_funds_minutes', 5)}m)",
            f"High network risk score ({network_risk:.1f})",
        ])
        
        alert_obj = create_alert(
            account_id=sender_id,
            risk_score=risk_score,
            risk_tier=risk_tier,
            summary=f"Real-time transaction alert for {sender_id} (${amount:,.2f} transfer to {receiver_id})",
            top_features=["txn_count_1h", "avg_time_to_forward_funds_minutes", "network_risk_score"],
            top_reasons=top_reasons,
            anomaly_score=anomaly_score,
            network_risk=network_risk,
            connected_suspicious_count=sender_features.get("unique_counterparty_count", 1),
            model_version=model_version,
            dedup_window_hours=12.0,  # 12-hour deduplication window
        )
        alert_created = True
        alert_id = alert_obj.get("alert_id")

    t1 = time.perf_counter()
    latency_ms = round((t1 - t0) * 1000.0, 2)

    output = {
        "transaction_id": txn_id,
        "prediction_time": pred_time_iso,
        "model_version": model_version,
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "amount": amount,
        "risk_score": risk_score,
        "risk_tier": risk_tier,
        "supervised_probability": supervised_prob,
        "anomaly_score": anomaly_score,
        "network_risk_score": network_risk,
        "latency_ms": latency_ms,
        "alert_created": alert_created,
        "alert_id": alert_id,
    }

    # Log Required Audit Telemetry Format
    audit_log = {
        "transaction_id": txn_id,
        "prediction_time": pred_time_iso,
        "model_version": model_version,
        "risk_score": risk_score,
        "latency": f"{latency_ms:.2f}ms",
        "alert_created": alert_created,
    }
    realtime_logger.info("REALTIME_SCORING_AUDIT: %s", json.dumps(audit_log))

    return output


# ---------------------------------------------------------------------------
# Kafka-Ready Abstract Event Consumer Design
# ---------------------------------------------------------------------------

class AbstractEventConsumer(abc.ABC):
    """
    Abstract Base Class defining the interface for transaction event consumers.
    Allows replacing LocalStreamConsumer with KafkaStreamConsumer in the future
    without altering ML inference or feature processing logic.
    """

    @abc.abstractmethod
    def consume_event(self, raw_event_payload: Any) -> Dict[str, Any]:
        """Parse raw event payload and invoke process_realtime_transaction."""
        pass

    @abc.abstractmethod
    def start_listening(self) -> None:
        """Start listening for incoming transaction stream events."""
        pass


class LocalStreamConsumer(AbstractEventConsumer):
    """
    Local event consumer implementation processing WebSocket/SSE HTTP transaction events.
    """

    def consume_event(self, raw_event_payload: Any) -> Dict[str, Any]:
        if isinstance(raw_event_payload, str):
            txn_dict = json.loads(raw_event_payload)
        else:
            txn_dict = dict(raw_event_payload)
        return process_realtime_transaction(txn_dict)

    def start_listening(self) -> None:
        logger.info("[LocalStreamConsumer] Started listening for local transaction stream events.")
