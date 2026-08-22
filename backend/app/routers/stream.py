"""
app/routers/stream.py
=======================
WebSocket & Server-Sent Events (SSE) streaming endpoints for real-time transaction scoring.

Endpoints:
  WS /ws/stream          — WebSocket live stream of real-time scored transaction events.
  GET /stream/events     — SSE EventSource stream of real-time scored transaction events.
  GET /stream/recent     — REST fallback endpoint for initial event buffer.
  POST /stream/score     — REST endpoint to ingest and score a single real-time transaction payload.
"""

import asyncio
import json
import logging
import random
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.realtime_pipeline import (
    TransactionValidationError,
    process_realtime_transaction,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["streaming"])

# Sample account pools for realistic stream event generation
_SENDER_POOL = [f"ACC-001{i:03d}" for i in range(1, 40)]
_RECEIVER_POOL = [f"ACC-002{i:03d}" for i in range(1, 40)]


class RealtimeTransactionPayload(BaseModel):
    transaction_id: str = Field(..., description="Unique transaction ID e.g. TXN-984123")
    sender_id: str = Field(..., description="Sender account ID e.g. ACC-001005")
    receiver_id: str = Field(..., description="Receiver account ID e.g. ACC-002012")
    amount: float = Field(..., gt=0, description="Transaction monetary amount")
    timestamp: str | None = Field(None, description="ISO 8601 UTC timestamp string")
    transaction_type: str | None = Field("TRANSFER", description="Transaction payment type")


def _generate_and_score_stream_event() -> dict:
    """Generate a raw transaction event and pass it through the 8-stage real-time pipeline."""
    sender_id = random.choice(_SENDER_POOL)
    receiver_id = random.choice(_RECEIVER_POOL)
    
    # 80% normal, 12% suspicious, 8% critical
    event_type = random.choices(["normal", "suspicious", "critical"], weights=[0.80, 0.12, 0.08])[0]
    
    if event_type == "critical":
        amount = round(random.uniform(15000, 95000), 2)
    elif event_type == "suspicious":
        amount = round(random.uniform(4500, 14999), 2)
    else:
        amount = round(random.uniform(25, 2800), 2)

    now_iso = datetime.now(timezone.utc).isoformat()
    raw_txn = {
        "transaction_id": f"TXN-{random.randint(100000, 999999)}",
        "sender_id": sender_id,
        "receiver_id": receiver_id,
        "amount": amount,
        "timestamp": now_iso,
        "transaction_type": "TRANSFER",
    }

    # Pass through 8-stage real-time scoring pipeline
    return process_realtime_transaction(raw_txn)


@router.post("/stream/score", summary="Score an incoming real-time transaction through 8-stage pipeline")
def score_realtime_event(body: RealtimeTransactionPayload) -> dict:
    """
    HTTP POST endpoint to score an incoming real-time transaction event payload.
    Flow: Validation → Feature Update → Account Retrieval → ML Inference → Anomaly Score → Network Lookup → Risk Fusion → Alert Generation.
    """
    try:
        raw_dict = body.model_dump()
        result = process_realtime_transaction(raw_dict)
        return result
    except TransactionValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to score real-time transaction: %s", exc)
        raise HTTPException(status_code=500, detail=f"Scoring error: {exc}") from exc


@router.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket) -> None:
    """
    WebSocket endpoint broadcasting real-time scored transaction events every 1 second.
    """
    await websocket.accept()
    logger.info("WebSocket client connected to /ws/stream")
    try:
        while True:
            event = _generate_and_score_stream_event()
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
            event = _generate_and_score_stream_event()
            yield f"data: {json.dumps(event)}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/stream/recent")
def get_recent_events(limit: int = 15) -> dict:
    """
    REST fallback endpoint returning a batch of recent real-time scored events.
    """
    events = [_generate_and_score_stream_event() for _ in range(limit)]
    return {
        "status": "ok",
        "count": len(events),
        "events": events,
    }
