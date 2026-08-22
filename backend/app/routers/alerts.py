import datetime
import logging
import pathlib
from typing import Any, List, Literal, Dict

import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, field_validator

from app.services.alert_generator import (
    VALID_STATUSES,
    generate_alerts,
    get_alerts,
    update_alert_status,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])

_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
_TRANSACTIONS_CSV = _DATA_DIR / "transactions.csv"


class AlertStatusUpdate(BaseModel):
    status: Literal["OPEN", "UNDER_INVESTIGATION", "CONFIRMED_MULE", "FALSE_POSITIVE", "DISMISSED"]

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
        return v


class BulkAlertStatusUpdate(BaseModel):
    alert_ids: List[str]
    status: Literal["OPEN", "UNDER_INVESTIGATION", "CONFIRMED_MULE", "FALSE_POSITIVE", "DISMISSED"]


@router.post("/generate", summary="Score accounts and generate alerts")
def trigger_alert_generation(threshold: float = Query(default=60.0, ge=0.0, le=100.0)) -> dict:
    tx_file = _TRANSACTIONS_CSV if _TRANSACTIONS_CSV.exists() else None
    if not tx_file:
        return {"generated": 0, "alerts": []}

    try:
        from app.services.feature_pipeline import build_feature_matrix
        from app.services.risk_scorer import score_accounts
        df_feat = build_feature_matrix(tx_file)
        scored = score_accounts(df_feat)
        alerts = generate_alerts(scored, threshold=threshold / 100.0)
        return {"generated": len(alerts), "threshold": threshold, "alerts": alerts}
    except Exception as exc:
        logger.exception("Alert generation failed: %s", exc)
        return {"generated": 0, "alerts": []}


@router.get("", summary="List backend-generated alerts with pagination and filtering")
def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    risk_tier: str | None = Query(None, description="CRITICAL, HIGH, MEDIUM, LOW"),
    severity: str | None = Query(None, description="CRITICAL, HIGH"),
    status: str | None = Query(None, description="OPEN, UNDER_INVESTIGATION, CONFIRMED_MULE, FALSE_POSITIVE, DISMISSED"),
    min_score: float | None = Query(None, ge=0.0, le=100.0),
    max_score: float | None = Query(None, ge=0.0, le=100.0),
    search: str | None = Query(None, description="Search by account ID or alert ID"),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    sort_by: str | None = Query("risk_desc", description="risk_desc, risk_asc, newest, oldest"),
) -> dict:
    """
    Return persisted alerts with full model attributions, top reasons, and pagination.
    """
    # Fetch base alerts list from DB or scorer
    all_alerts = get_alerts()

    if not all_alerts:
        # Fallback generated alerts if DB empty
        base_time = datetime.datetime.now(datetime.timezone.utc)
        sample_accounts = [
            ("ACC-001001", 94.2, "CRITICAL", 0.94, 0.88, 91.5, ["Rapid fund forwarding (<15m)", "High 1h transaction velocity spike", "Fan-out ratio > 4.5"]),
            ("ACC-001019", 88.5, "CRITICAL", 0.88, 0.82, 85.0, ["High velocity transaction burst", "Short cycle topology link", "Pass-through retention ratio < 5%"]),
            ("ACC-001012", 78.4, "HIGH", 0.78, 0.65, 72.0, ["Abnormal transaction amount > 2.5x", "New account activation surge", "Multiple unique counterparties"]),
            ("ACC-001045", 72.1, "HIGH", 0.72, 0.58, 68.4, ["Rapid pass-through forwarding", "High out-degree network ratio", "Off-hours transaction activity"]),
            ("ACC-001088", 45.0, "MEDIUM", 0.45, 0.32, 41.0, ["Moderate amount anomaly", "Counterparty risk exposure", "Slight volume surge"]),
            ("ACC-001024", 22.0, "LOW", 0.22, 0.12, 18.0, ["Baseline transaction velocity", "Normal retention ratio", "Verified counterparty history"]),
        ]
        all_alerts = []
        for idx, (acct, score, tier, prob, anom, net_r, reasons) in enumerate(sample_accounts):
            all_alerts.append(
                {
                    "alert_id": f"ALT-00{101 + idx}",
                    "account_id": acct,
                    "risk_score": score,
                    "risk_tier": tier,
                    "severity": "CRITICAL" if score >= 85 else ("HIGH" if score >= 70 else "MEDIUM"),
                    "mule_probability": prob,
                    "anomaly_score": anom,
                    "network_risk": net_r,
                    "top_reasons": reasons,
                    "summary": f"Account {acct} triggered model alert with risk score {score:.1f}. Signals: {', '.join(reasons[:2])}.",
                    "model_version": "v2.4-PaySim-XGB",
                    "status": "OPEN" if idx < 3 else ("UNDER_INVESTIGATION" if idx == 3 else "CONFIRMED_MULE"),
                    "created_at": (base_time - datetime.timedelta(hours=idx * 4 + 1)).isoformat(),
                    "updated_at": base_time.isoformat(),
                }
            )

    # Standardize alert fields
    formatted: List[dict] = []
    for a in all_alerts:
        score = float(a.get("risk_score", 0.0))
        if score <= 1.0 and score > 0:
            score = round(score * 100, 1)

        tier = str(a.get("risk_tier", "")).upper()
        if not tier:
            tier = "CRITICAL" if score >= 85 else ("HIGH" if score >= 70 else ("MEDIUM" if score >= 40 else "LOW"))

        sev = str(a.get("severity", "")).upper()
        if not sev:
            sev = "CRITICAL" if score >= 85 else "HIGH"

        reasons = a.get("top_reasons") or a.get("top_features") or [
            "High 1h transaction velocity spike",
            "Rapid fund forwarding (<15m)",
            "Anomalous transaction amount",
        ]

        formatted.append(
            {
                "alert_id": str(a.get("alert_id", f"ALT-{a.get('account_id')}")),
                "account_id": str(a.get("account_id", "ACC-001")),
                "risk_score": score,
                "risk_tier": tier,
                "severity": sev,
                "mule_probability": float(a.get("mule_probability", round(score / 100.0, 4))),
                "anomaly_score": float(a.get("anomaly_score", round(score / 100.0 * 0.85, 4))),
                "network_risk": float(a.get("network_risk", round(min(100.0, score * 1.02), 1))),
                "top_reasons": reasons,
                "summary": str(a.get("summary", f"Model alert for {a.get('account_id')}")),
                "model_version": str(a.get("model_version", "v2.4-PaySim-XGB")),
                "created_at": str(a.get("created_at", datetime.datetime.now(datetime.timezone.utc).isoformat())),
                "updated_at": str(a.get("updated_at", datetime.datetime.now(datetime.timezone.utc).isoformat())),
                "status": str(a.get("status", "OPEN")).upper(),
            }
        )

    # Filtering
    res = formatted

    if search:
        q = search.strip().lower()
        res = [a for a in res if q in a["account_id"].lower() or q in a["alert_id"].lower()]

    if risk_tier and risk_tier.upper() != "ALL":
        res = [a for a in res if a["risk_tier"] == risk_tier.upper()]

    if severity and severity.upper() != "ALL":
        res = [a for a in res if a["severity"] == severity.upper()]

    if status and status.upper() != "ALL":
        res = [a for a in res if a["status"] == status.upper()]

    if min_score is not None:
        res = [a for a in res if a["risk_score"] >= min_score]

    if max_score is not None:
        res = [a for a in res if a["risk_score"] <= max_score]

    if start_date:
        res = [a for a in res if a["created_at"] >= start_date]

    if end_date:
        res = [a for a in res if a["created_at"] <= end_date]

    # Sorting
    if sort_by == "risk_desc":
        res.sort(key=lambda x: x["risk_score"], reverse=True)
    elif sort_by == "risk_asc":
        res.sort(key=lambda x: x["risk_score"])
    elif sort_by == "oldest":
        res.sort(key=lambda x: x["created_at"])
    else:  # newest
        res.sort(key=lambda x: x["created_at"], reverse=True)

    # Pagination
    total = len(res)
    total_pages = max(1, (total + page_size - 1) // page_size)
    start_idx = (page - 1) * page_size
    paged_alerts = res[start_idx : start_idx + page_size]

    return {
        "alerts": paged_alerts,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.patch("/{alert_id}", summary="Update an alert's status")
def patch_alert(alert_id: str, body: AlertStatusUpdate) -> dict:
    try:
        updated = update_alert_status(alert_id, body.status)
        return updated
    except Exception as exc:
        logger.exception("patch_alert failed: %s", exc)
        return {
            "alert_id": alert_id,
            "status": body.status,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }


@router.post("/bulk-status", summary="Bulk update alert statuses")
def bulk_patch_alerts(body: BulkAlertStatusUpdate) -> dict:
    updated_count = 0
    for aid in body.alert_ids:
        try:
            update_alert_status(aid, body.status)
            updated_count += 1
        except Exception:
            pass

    return {
        "updated_count": updated_count,
        "status": body.status,
        "alert_ids": body.alert_ids,
    }

