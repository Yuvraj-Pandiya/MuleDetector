"""
app/main.py
============
MuleDetector API — FastAPI application entry point.

Routers registered (Track B — ml-api):
    /health            liveness probe
    /train             model training
    /predict/*         risk scoring + SHAP explanations
    /alerts/*          alert management (SQLite-backed)
    /dashboard/*       operational summary

Middleware / exception handling:
    - CORSMiddleware   (all origins during dev; tighten in prod)
    - RequestLoggingMiddleware  (method, path, status, latency on every req)
    - Global exception handler  (clean JSON errors; no raw Python tracebacks)
"""

from __future__ import annotations

import logging
import time
import traceback

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import alerts, dashboard, features, graph, health, predict, train, upload

logger = logging.getLogger("mule_detector")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


app = FastAPI(
    title="MuleDetector API",
    description=(
        "ML-powered money mule detection service.  "
        "Train → Score → Explain → Alert → Dashboard."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# Global exception handler — no raw tracebacks in responses
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all for any unhandled exception.

    Returns a clean JSON body:
        {"error": "<type>", "detail": "<message>"}

    The full traceback is logged server-side at ERROR level.
    """
    tb = traceback.format_exc()
    logger.error(
        "Unhandled exception on %s %s\n%s",
        request.method,
        request.url.path,
        tb,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": type(exc).__name__,
            "detail": str(exc) or "An unexpected server error occurred.",
        },
    )


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log every request with method, path, status code, and latency (ms)."""
    t0 = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
    logger.info(
        "%s  %s  →  %d  (%.1f ms)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers  (Track B — ml-api)
# ---------------------------------------------------------------------------

app.include_router(health.router)
app.include_router(train.router)
app.include_router(predict.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)
app.include_router(upload.router)
app.include_router(features.router)
app.include_router(graph.router)
