from __future__ import annotations

import datetime
import logging
import pathlib
from typing import Any, List, Optional

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
    status: str

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in VALID_STATUSES:
            raise ValueError(f"status must be one of {sorted(VALID_STATUSES)}")
        return v_upper


class BulkAlertStatusUpdate(BaseModel):
    alert_ids: List[str]
    status: str


@router.post("/generate", summary="Score accounts and generate prioritized risk-based alerts")
def trigger_alert_generation(threshold: float = Query(default=30.0, ge=0.0, le=100.0)) -> dict:
    tx_file = _TRANSACTIONS_CSV if _TRANSACTIONS_CSV.exists() else None
    if not tx_file:
        return {"generated": 0, "alerts": []}

    try:
        from app.services.feature_pipeline import build_feature_matrix
        from app.services.risk_scorer import score_accounts
        df_feat = build_feature_matrix(tx_file)
        scored = score_accounts(df_feat)
        alerts = generate_alerts(scored, threshold=threshold)
        return {"generated": len(alerts), "threshold": threshold, "alerts": alerts}
    except Exception as exc:
        logger.exception("Alert generation failed: %s", exc)
        return {"generated": 0, "alerts": []}


@router.get("", summary="List backend-generated alerts with pagination and prioritized queue sorting")
def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    risk_tier: Optional[str] = Query(None, description="CRITICAL, HIGH, MEDIUM, LOW"),
    severity: Optional[str] = Query(None, description="CRITICAL, HIGH, MEDIUM, LOW"),
    status: Optional[str] = Query(None, description="OPEN, UNDER_INVESTIGATION, CONFIRMED_MULE, FALSE_POSITIVE, DISMISSED"),
    min_score: Optional[float] = Query(None, ge=0.0, le=100.0),
    max_score: Optional[float] = Query(None, ge=0.0, le=100.0),
    search: Optional[str] = Query(None, description="Search by account ID or alert ID"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("prioritized", description="prioritized, risk_desc, risk_asc, newest, oldest"),
) -> dict:
    """
    Return persisted alerts sorted by prioritized analyst queue criteria:
      1. risk_score DESC
      2. severity DESC (CRITICAL > HIGH > MEDIUM > LOW)
      3. network_risk DESC
      4. connected_suspicious_count DESC
    """
    all_alerts = get_alerts(severity=severity, status=status, risk_tier=risk_tier, sort_by=sort_by or "prioritized")

    if not all_alerts:
        # Fallback sample alerts if DB empty
        base_time = datetime.datetime.now(datetime.timezone.utc)
        sample_accounts = [
            ("ACC-001001", 94.2, "CRITICAL", 0.94, 0.88, 91.5, ["unusually high outgoing velocity", "rapid fund forwarding", "large number of counterparties"]),
            ("ACC-001019", 88.5, "CRITICAL", 0.88, 0.82, 85.0, ["high velocity transaction burst", "participation in rapid circular fund pass-through"]),
            ("ACC-001012", 78.4, "HIGH", 0.78, 0.65, 72.0, ["abnormally high average transaction size", "large number of counterparties"]),
            ("ACC-001045", 72.1, "HIGH", 0.72, 0.58, 68.4, ["rapid fund forwarding", "high fan-out distribution ratio"]),
            ("ACC-001088", 45.0, "MEDIUM", 0.45, 0.32, 41.0, ["moderate amount anomaly", "counterparty risk exposure"]),
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
                    "connected_suspicious_count": 5 if score >= 85 else 2,
                    "top_reasons": reasons,
                    "top_features": reasons,
                    "summary": f"Account {acct} triggered model alert with risk score {score:.1f}. Signals: {', '.join(reasons[:2])}.",
                    "model_version": "v2.5.0-XGBoost",
                    "status": "OPEN" if idx < 3 else ("UNDER_INVESTIGATION" if idx == 3 else "CONFIRMED_MULE"),
                    "created_at": (base_time - datetime.timedelta(hours=idx * 4 + 1)).isoformat(),
                    "updated_at": base_time.isoformat(),
                }
            )

    # Standardize alert records
    formatted: List[dict] = []
    for a in all_alerts:
        score = float(a.get("risk_score", 0.0))
        if score <= 1.0 and score > 0:
            score = round(score * 100, 1)

        tier = str(a.get("risk_tier", "")).upper()
        if not tier:
            tier = "CRITICAL" if score >= 85 else ("HIGH" if score >= 70 else ("MEDIUM" if score >= 30 else "LOW"))

        sev = str(a.get("severity", "")).upper()
        if not sev:
            sev = "CRITICAL" if score >= 85 else ("HIGH" if score >= 70 else "MEDIUM")

        reasons = a.get("top_reasons") or a.get("top_features") or ["unusually high outgoing velocity", "rapid fund forwarding"]

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
                "connected_suspicious_count": int(a.get("connected_suspicious_count", 0)),
                "top_reasons": reasons,
                "summary": str(a.get("summary", f"Model alert for {a.get('account_id')}")),
                "model_version": str(a.get("model_version", "v2.5.0-XGBoost")),
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

    # Prioritized Sorting
    if sort_by == "prioritized":
        sev_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        res.sort(
            key=lambda x: (
                x["risk_score"],
                sev_rank.get(x["severity"], 1),
                x["network_risk"],
                x["connected_suspicious_count"],
                x["created_at"],
            ),
            reverse=True,
        )
    elif sort_by == "risk_desc":
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
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")
    except Exception as exc:
        logger.exception("patch_alert failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


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
