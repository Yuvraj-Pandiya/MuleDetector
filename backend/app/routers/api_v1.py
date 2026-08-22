"""
app/routers/api_v1.py
========================
Canonical API routes under /api/... mapping directly to core pipeline services.

Endpoints included:
- GET  /api/dashboard/summary
- GET  /api/accounts
- GET  /api/accounts/{accountId}
- GET  /api/accounts/{accountId}/transactions
- GET  /api/accounts/{accountId}/fund-flow
- GET  /api/accounts/{accountId}/network
- GET  /api/accounts/{accountId}/explanation
- GET  /api/alerts
- GET  /api/alerts/{alertId}
- POST /api/alerts/{alertId}/decision
- POST /api/accounts/{accountId}/notes
- GET  /api/models
- GET  /api/models/{version}/metrics
- GET  /api/models/{version}/features
- GET  /api/anomalies
- GET  /api/network/{accountId}
- GET  /api/monitoring/drift
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app.routers import alerts, dashboard, feature_selection, graph, predict, train, feedback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["canonical_api"])


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@router.get("/dashboard/summary")
def get_api_dashboard_summary() -> dict:
    """Canonical GET /api/dashboard/summary endpoint."""
    return dashboard.get_dashboard_summary()


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------
@router.get("/accounts")
def get_api_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
    min_risk: Optional[float] = Query(None),
    max_risk: Optional[float] = Query(None),
    risk_tier: Optional[str] = Query(None),
    sort_by: str = Query("risk_score_desc"),
    search: Optional[str] = Query(None),
) -> dict:
    """Canonical GET /api/accounts endpoint."""
    return predict.get_accounts_paginated(
        page=page,
        page_size=page_size,
        min_risk=min_risk,
        max_risk=max_risk,
        risk_tier=risk_tier,
        sort_by=sort_by,
        search=search,
    )


@router.get("/accounts/{accountId}")
def get_api_account_details(accountId: str) -> dict:
    """Canonical GET /api/accounts/{accountId} endpoint."""
    return predict.get_account_details(accountId)


@router.get("/accounts/{accountId}/transactions")
def get_api_account_transactions(
    accountId: str,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    min_amount: Optional[float] = Query(None),
    max_amount: Optional[float] = Query(None),
    direction: Optional[str] = Query(None),
) -> dict:
    """Canonical GET /api/accounts/{accountId}/transactions endpoint."""
    return predict.get_account_transactions(
        account_id=accountId,
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount,
        max_amount=max_amount,
        direction=direction,
    )


@router.get("/accounts/{accountId}/fund-flow")
def get_api_account_fund_flow(accountId: str) -> dict:
    """Canonical GET /api/accounts/{accountId}/fund-flow endpoint."""
    return predict.get_account_fund_flow(accountId)


@router.get("/accounts/{accountId}/network")
def get_api_account_network(accountId: str, max_hops: int = Query(2, ge=1, le=4)) -> dict:
    """Canonical GET /api/accounts/{accountId}/network endpoint."""
    return graph.get_account_ego_network(account_id=accountId, max_hops=max_hops)


@router.get("/accounts/{accountId}/explanation")
def get_api_account_explanation(accountId: str) -> dict:
    """Canonical GET /api/accounts/{accountId}/explanation endpoint."""
    return predict.get_explanation(accountId)


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------
@router.get("/alerts")
def get_api_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
    status: Optional[str] = Query(None),
    risk_tier: Optional[str] = Query(None),
    min_risk: Optional[float] = Query(None),
    max_risk: Optional[float] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("newest"),
) -> dict:
    """Canonical GET /api/alerts endpoint."""
    return alerts.get_alerts_list(
        page=page,
        page_size=page_size,
        status=status,
        risk_tier=risk_tier,
        min_risk=min_risk,
        max_risk=max_risk,
        search=search,
        sort_by=sort_by,
    )


@router.get("/alerts/{alertId}")
def get_api_alert_details(alertId: str) -> dict:
    """Canonical GET /api/alerts/{alertId} endpoint."""
    return alerts.get_alert_details(alertId)


@router.post("/alerts/{alertId}/decision")
def post_api_alert_decision(alertId: str, payload: dict) -> dict:
    """Canonical POST /api/alerts/{alertId}/decision endpoint."""
    payload["alert_id"] = alertId
    return alerts.post_alert_decision(payload)


@router.post("/accounts/{accountId}/notes")
def post_api_account_notes(accountId: str, payload: dict) -> dict:
    """Canonical POST /api/accounts/{accountId}/notes endpoint."""
    payload["account_id"] = accountId
    return feedback.add_investigator_note(payload)


# ---------------------------------------------------------------------------
# Models & Feature Intelligence
# ---------------------------------------------------------------------------
@router.get("/models")
def get_api_models() -> dict:
    """Canonical GET /api/models endpoint."""
    return train.get_model_performance()


@router.get("/models/{version}/metrics")
def get_api_model_version_metrics(version: str) -> dict:
    """Canonical GET /api/models/{version}/metrics endpoint."""
    res = train.get_model_performance()
    res["requested_version"] = version
    return res


@router.get("/models/{version}/features")
def get_api_model_version_features(version: str) -> dict:
    """Canonical GET /api/models/{version}/features endpoint."""
    res = feature_selection.get_feature_intelligence()
    res["requested_version"] = version
    return res


# ---------------------------------------------------------------------------
# Anomalies & Network Graph
# ---------------------------------------------------------------------------
@router.get("/anomalies")
def get_api_anomalies(
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
    min_anomaly: Optional[float] = Query(None),
    sort_by: str = Query("highest_anomaly"),
) -> dict:
    """Canonical GET /api/anomalies endpoint."""
    return predict.get_anomaly_summary(
        page=page,
        page_size=page_size,
        min_anomaly=min_anomaly,
        sort_by=sort_by,
    )


@router.get("/network/{accountId}")
def get_api_network_account(accountId: str, max_hops: int = Query(2, ge=1, le=4)) -> dict:
    """Canonical GET /api/network/{accountId} endpoint."""
    return graph.get_account_ego_network(account_id=accountId, max_hops=max_hops)


# ---------------------------------------------------------------------------
# Monitoring & Drift
# ---------------------------------------------------------------------------
@router.get("/monitoring/drift")
def get_api_monitoring_drift() -> dict:
    """Canonical GET /api/monitoring/drift endpoint."""
    return train.get_model_monitoring()
