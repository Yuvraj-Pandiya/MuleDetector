"""
app/main.py
============
MuleDetector API — FastAPI application entry point.

Routers registered:
    /health               liveness probe
    /train                model training
    /predict/*            risk scoring + SHAP explanations
    /alerts/*             alert management (SQLite-backed)
    /dashboard/*          operational summary
    /graph/*              network topology
    /features             raw features
    /upload-dataset       CSV dataset ingestion
    /feature-selection/*  feature ranking & importance analysis

Middleware / exception handling:
    - CORSMiddleware   (all origins allowed)
    - RequestLoggingMiddleware  (method, path, status, latency)
    - Global exception handler  (clean JSON errors with CORS headers)
"""

from __future__ import annotations

import logging
import time
import traceback

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import alerts, api_v1, dashboard, datasets, feature_selection, features, feedback, graph, health, predict, retrain, sar, stream, train, upload

logger = logging.getLogger("mule_detector")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

from contextlib import asynccontextmanager
from pathlib import Path

_DATA_DIR = Path(__file__).parent / "data"

@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup: initialize datasets registry and verify benchmark dataset."""
    try:
        from app.services.dataset_registry import list_datasets, get_active_dataset
        ds_list = list_datasets()
        active = get_active_dataset()
        logger.info("[Startup] Dataset Registry initialized with %d datasets. Active: '%s'", len(ds_list), active.get("name"))
    except Exception as _e:
        logger.warning("[Startup] Could not initialize dataset registry: %s", _e)
    yield  # app runs here

app = FastAPI(
    title="MuleDetector API",
    description=(
        "ML-powered money mule detection service.  "
        "Train → Score → Explain → Alert → Dashboard → HITL Retraining."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS Middleware (Outer middleware)
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global exception handler — clean JSON errors with CORS headers
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all for any unhandled exception.
    """
    tb = traceback.format_exc()
    logger.error("Unhandled exception on %s %s\n%s", request.method, request.url.path, tb)
    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": type(exc).__name__,
            "detail": str(exc) or "An unexpected server error occurred.",
        },
    )
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log every request with method, path, status code, and latency (ms)."""
    raw_path = request.scope.get("path", "")
    if raw_path.endswith(" ") or raw_path.endswith("%20"):
        request.scope["path"] = raw_path.rstrip(" %20")

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
# Routers
# ---------------------------------------------------------------------------

app.include_router(health.router)
app.include_router(train.router)
app.include_router(predict.router)
app.include_router(alerts.router)
app.include_router(dashboard.router)
app.include_router(upload.router)
app.include_router(datasets.router)
app.include_router(features.router)
app.include_router(graph.router)
app.include_router(feature_selection.router)
app.include_router(feedback.router)
app.include_router(retrain.router)
app.include_router(stream.router)
app.include_router(sar.router)
app.include_router(api_v1.router)


