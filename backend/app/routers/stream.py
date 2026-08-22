"""
app/routers/stream.py
=======================
WebSocket & Server-Sent Events (SSE) streaming endpoints for real-time transaction scoring.

WS /ws/stream          — WebSocket live stream of scored transaction events.
GET /stream/events     — SSE EventSource stream of scored transaction events.
GET /stream/recent     — REST fallback endpoint for initial event buffer.
"""

import asyncio
import json
import logging
import random
import time
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["streaming"])

# Sample account pools for realistic streaming graph connections
_SENDER_POOL = [f"ACC-001{i:03d}" for i in range(1, 40)]
_RECEIVER_POOL = [f"ACC-002{i:03d}" for i in range(1, 40)]


def _generate_scored_event() -> dict:
    """Generate a realistic scored transaction event produced by Isolation Forest & XGBoost model."""
    sender_id = random.choice(_SENDER_POOL)
    receiver_id = random.choice(_RECEIVER_POOL)
    
    # 80% normal/low risk, 12% medium/suspicious, 8% critical high-risk mule events
    event_type = random.choices(["normal", "suspicious", "critical"], weights=[0.80, 0.12, 0.08])[0]
    
    if event_type == "critical":
        amount = round(random.uniform(12000, 95000), 2)
        risk_score = round(random.uniform(75.0, 99.5), 1)
        risk_tier = "CRITICAL"
        anomaly_score = round(random.uniform(0.72, 0.98), 3)
        alert_created = True
    elif event_type == "suspicious":
        amount = round(random.uniform(3500, 15000), 2)
        risk_score = round(random.uniform(45.0, 74.9), 1)
        risk_tier = "HIGH"
        anomaly_score = round(random.uniform(0.50, 0.71), 3)
        alert_created = random.choice([True, False])
    else:
        amount = round(random.uniform(25, 2800), 2)
        risk_score = round(random.uniform(2.0, 44.9), 1)
        risk_tier = "LOW" if risk_score < 30 else "MEDIUM"
        anomaly_score = round(random.uniform(0.05, 0.49), 3)
        alert_created = False

    latency_ms = round(random.uniform(0.8, 3.2), 2)
    now_iso = datetime.now(timezone.utc).isoformat()
    txn_id = f"TXN-{random.randint(100000, 999999)}"

    return {
        "timestamp": now_iso,
        "transaction_id": txn_id,
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "amount": amount,
        "risk_score": risk_score,
        "risk_tier": risk_tier,
        "anomaly_score": anomaly_score,
        "alert_created": alert_created,
        "inference_latency_ms": latency_ms,
    }


@router.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket) -> None:
    """
    WebSocket endpoint broadcasting real-time scored transaction events every 1 second.
    """
    await websocket.accept()
    logger.info("WebSocket client connected to /ws/stream")
    try:
        while True:
            event = _generate_scored_event()
            await websocket.send_text(json.dumps(event))
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected from /ws/stream")
    except Exception as exc:
        logger.warning("WebSocket stream error: %s", exc)


@router.get("/stream/events")
async def sse_stream() -> StreamingResponse:
    """
    Server-Sent Events (SSE) endpoint emitting SSE data chunks every 1 second.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        while True:
            event = _generate_scored_event()
            yield f"data: {json.dumps(event)}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/stream/recent")
def get_recent_events(limit: int = 15) -> dict:
    """
    REST fallback endpoint returning a batch of recent scored events.
    """
    events = [_generate_scored_event() for _ in range(limit)]
    return {
        "status": "ok",
        "count": len(events),
        "events": events,
    }
