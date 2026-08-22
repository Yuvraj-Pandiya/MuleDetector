"""
app/services/sar_store.py
==========================
Persist and retrieve Suspicious Activity Reports (SAR) drafts and final filings.
"""

import datetime
import json
import logging
import pathlib
import sqlite3
from contextlib import contextmanager
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
DB_PATH = _DATA_DIR / "sar.db"

def bootstrap_sar_db() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sars (
                sar_id             TEXT PRIMARY KEY,
                account_id         TEXT NOT NULL,
                alert_id           TEXT,
                status             TEXT NOT NULL, -- 'DRAFT', 'SUBMITTED'
                filing_date        TEXT NOT NULL,
                narrative          TEXT NOT NULL,
                risk_score         REAL,
                risk_tier          TEXT,
                anomaly_score      REAL,
                top_features       TEXT, -- JSON list of features
                investigator       TEXT NOT NULL,
                created_at         TEXT NOT NULL,
                updated_at         TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sar_account ON sars(account_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sar_status ON sars(status)")

@contextmanager
def _get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_sar_by_id(sar_id: str) -> Optional[dict]:
    bootstrap_sar_db()
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM sars WHERE sar_id = ?", (sar_id,)).fetchone()
    if not row:
        return None
    res = dict(row)
    if res.get("top_features"):
        try:
            res["top_features"] = json.loads(res["top_features"])
        except Exception:
            res["top_features"] = []
    return res

def get_sar_by_account(account_id: str) -> Optional[dict]:
    bootstrap_sar_db()
    with _get_conn() as conn:
        row = conn.execute("SELECT * FROM sars WHERE account_id = ? ORDER BY updated_at DESC LIMIT 1", (account_id,)).fetchone()
    if not row:
        return None
    res = dict(row)
    if res.get("top_features"):
        try:
            res["top_features"] = json.loads(res["top_features"])
        except Exception:
            res["top_features"] = []
    return res

def list_all_sars() -> List[dict]:
    bootstrap_sar_db()
    with _get_conn() as conn:
        rows = conn.execute("SELECT * FROM sars ORDER BY updated_at DESC").fetchall()
    results = []
    for r in rows:
        d = dict(r)
        if d.get("top_features"):
            try:
                d["top_features"] = json.loads(d["top_features"])
            except Exception:
                d["top_features"] = []
        results.append(d)
    return results

def upsert_sar(
    sar_id: str,
    account_id: str,
    alert_id: Optional[str],
    status: str,
    narrative: str,
    risk_score: float,
    risk_tier: str,
    anomaly_score: float,
    top_features: List[str],
    investigator: str,
) -> dict:
    bootstrap_sar_db()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    features_json = json.dumps(top_features)

    with _get_conn() as conn:
        existing = conn.execute("SELECT sar_id, created_at FROM sars WHERE sar_id = ?", (sar_id,)).fetchone()
        if existing:
            created_at = existing["created_at"]
            conn.execute(
                """
                UPDATE sars
                SET account_id = ?, alert_id = ?, status = ?, narrative = ?, risk_score = ?,
                    risk_tier = ?, anomaly_score = ?, top_features = ?, investigator = ?, updated_at = ?
                WHERE sar_id = ?
                """,
                (account_id, alert_id, status, narrative, risk_score, risk_tier, anomaly_score, features_json, investigator, now_iso, sar_id),
            )
        else:
            created_at = now_iso
            conn.execute(
                """
                INSERT INTO sars (sar_id, account_id, alert_id, status, filing_date, narrative, risk_score, risk_tier, anomaly_score, top_features, investigator, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (sar_id, account_id, alert_id, status, now_iso[:10], narrative, risk_score, risk_tier, anomaly_score, features_json, investigator, created_at, now_iso),
            )

    return {
        "sar_id": sar_id,
        "account_id": account_id,
        "alert_id": alert_id,
        "status": status,
        "filing_date": now_iso[:10],
        "narrative": narrative,
        "risk_score": risk_score,
        "risk_tier": risk_tier,
        "anomaly_score": anomaly_score,
        "top_features": top_features,
        "investigator": investigator,
        "created_at": created_at,
        "updated_at": now_iso,
    }
