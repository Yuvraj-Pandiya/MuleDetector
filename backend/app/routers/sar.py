"""
app/routers/sar.py
===================
FastAPI Router for Suspicious Activity Report (SAR) drafts and submissions.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.sar_store import (
    get_sar_by_id,
    get_sar_by_account,
    list_all_sars,
    upsert_sar,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sar", tags=["sar"])

class SarPayload(BaseModel):
    sar_id: str
    account_id: str
    alert_id: Optional[str] = None
    status: str  # 'DRAFT' or 'SUBMITTED'
    narrative: str
    risk_score: float
    risk_tier: str
    anomaly_score: float
    top_features: List[str]
    investigator: Optional[str] = "Analyst #402"

def _generate_default_narrative(
    account_id: str,
    risk_score: float,
    risk_tier: str,
    anomaly_score: float,
    top_features: List[str]
) -> str:
    features_list = top_features if top_features else ["unusually high outgoing velocity", "rapid fund forwarding"]
    features_str = ", ".join(features_list)
    
    return (
        f"SUSPICIOUS ACTIVITY REPORT NARRATIVE - CONFIDENTIAL\n"
        f"==================================================\n\n"
        f"MuleScope AI transaction monitoring detected highly suspicious activities associated with Subject Account ID: {account_id}.\n\n"
        f"DETAILED EVIDENCE:\n"
        f"1. Risk Score: {risk_score}/100, classified in the '{risk_tier.upper()}' risk tier.\n"
        f"2. Unsupervised Anomaly Percentile: {anomaly_score:.2f}.\n"
        f"3. Identified Behavioral Anomalies: {features_str}.\n\n"
        f"NARRATIVE SUMMARY:\n"
        f"The account {account_id} has demonstrated structural patterns consistent with Money Mule activity (specifically rapid pass-through/layering behavior). "
        f"Transaction velocities are significantly higher than the baseline average for this peer group. Funds received are dispersed to external counterparties "
        f"with a very low latency, leaving minimal balance. This is indicative of structured credit/debit routing aimed at bypassing transaction thresholds.\n\n"
        f"INVESTIGATIVE STATUS:\n"
        f"This report is drafted for formal submission to regulatory units. Further identity cross-matching (KYC) and transaction verification are strongly recommended."
    )

@router.get("", summary="List all saved SAR reports (drafts and filings)")
def list_sars() -> List[dict]:
    try:
        return list_all_sars()
    except Exception as exc:
        logger.exception("Failed to list SAR reports: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/account/{account_id}", summary="Get existing SAR or generate a default pre-filled draft")
def get_or_create_sar_draft(account_id: str) -> dict:
    try:
        existing = get_sar_by_account(account_id)
        if existing:
            return existing

        # Fallback: get data from predict to pre-fill
        from app.routers.predict import _load_feature_df
        from app.services.risk_scorer import score_accounts
        
        df = _load_feature_df()
        scored = score_accounts(df)
        match = scored[scored["account_id"] == account_id]
        
        if match.empty:
            risk_score = 75.0
            risk_tier = "HIGH"
            anomaly_score = 0.65
            top_features = ["high velocity transaction burst", "unusually high outgoing velocity"]
        else:
            row = match.iloc[0]
            risk_score = float(row.get("risk_score", 50.0))
            if risk_score <= 1.0:
                risk_score = round(risk_score * 100.0, 1)
            risk_tier = str(row.get("risk_tier", "MEDIUM")).upper()
            anomaly_score = float(row.get("anomaly_score", 0.5))
            top_features = list(row.get("top_features", ["rapid fund forwarding", "large number of counterparties"]))
            
        sar_id = f"SAR-{account_id}"
        narrative = _generate_default_narrative(
            account_id=account_id,
            risk_score=risk_score,
            risk_tier=risk_tier,
            anomaly_score=anomaly_score,
            top_features=top_features
        )
        
        import datetime
        now_date = datetime.datetime.now(datetime.timezone.utc).isoformat()[:10]
        
        return {
            "sar_id": sar_id,
            "account_id": account_id,
            "alert_id": f"ALT-{account_id}",
            "status": "DRAFT",
            "filing_date": now_date,
            "narrative": narrative,
            "risk_score": risk_score,
            "risk_tier": risk_tier,
            "anomaly_score": anomaly_score,
            "top_features": top_features,
            "investigator": "Analyst #402",
            "created_at": "",
            "updated_at": ""
        }
    except Exception as exc:
        logger.exception("Failed to get/generate SAR: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

@router.get("/{sar_id}", summary="Get details of a specific SAR by its ID")
def get_sar(sar_id: str) -> dict:
    res = get_sar_by_id(sar_id)
    if not res:
        raise HTTPException(status_code=404, detail=f"SAR report with ID {sar_id} not found.")
    return res

@router.post("", summary="Create or update a SAR report (Save Draft or Submit)")
def save_sar(body: SarPayload) -> dict:
    try:
        res = upsert_sar(
            sar_id=body.sar_id,
            account_id=body.account_id,
            alert_id=body.alert_id,
            status=body.status.upper(),
            narrative=body.narrative,
            risk_score=body.risk_score,
            risk_tier=body.risk_tier,
            anomaly_score=body.anomaly_score,
            top_features=body.top_features,
            investigator=body.investigator or "Analyst #402",
        )
        
        # Sync back to feedback DB on submission
        if body.status.upper() == "SUBMITTED":
            try:
                from app.services.feedback_store import submit_feedback
                submit_feedback(
                    alert_id=body.alert_id or f"ALT-{body.account_id}",
                    account_id=body.account_id,
                    decision="CONFIRMED_MULE",
                    note=f"Filing SAR {body.sar_id}: {body.narrative[:100]}...",
                    investigator=body.investigator or "Analyst #402",
                )
            except Exception as e:
                logger.warning("Failed to sync feedback on SAR submit: %s", e)
                
        return res
    except Exception as exc:
        logger.exception("Failed to save SAR report: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
