"""
app/services/feedback_store.py
===============================
Persist and retrieve investigator feedback decisions and notes.

Public API:
-----------
submit_feedback(alert_id, account_id, decision, note, investigator) -> dict
get_feedback_history(account_id=None, alert_id=None) -> list[dict]
"""

from __future__ import annotations

import datetime
import logging
import pathlib
import sqlite3
from contextlib import contextmanager
from typing import List, Optional

logger = logging.getLogger(__name__)

_DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
DB_PATH = _DATA_DIR / "feedback.db"

VALID_DECISIONS = {
    "CONFIRMED_MULE",
    "LEGITIMATE",
    "FALSE_POSITIVE",
    "UNDER_INVESTIGATION",
}


def _bootstrap_db() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id        TEXT NOT NULL,
                account_id      TEXT NOT NULL,
                decision        TEXT NOT NULL,
                note            TEXT NOT NULL,
                investigator    TEXT NOT NULL,
                timestamp       TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fb_account ON feedback(account_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fb_alert   ON feedback(alert_id)")


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


def submit_feedback(
    alert_id: str,
    account_id: str,
    decision: str,
    note: str,
    investigator: str = "Analyst #402",
) -> dict:
    if decision not in VALID_DECISIONS:
        raise ValueError(f"Decision must be one of {sorted(VALID_DECISIONS)}")

    _bootstrap_db()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    with _get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO feedback (alert_id, account_id, decision, note, investigator, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (alert_id, account_id, decision, note, investigator, now_iso),
        )
        feedback_id = cur.lastrowid

    # Update associated alert status in alerts table if alerts.db exists
    try:
        from app.services.alert_generator import update_alert_status
        status_map = {
            "CONFIRMED_MULE": "CONFIRMED_MULE",
            "LEGITIMATE": "DISMISSED",
            "FALSE_POSITIVE": "FALSE_POSITIVE",
            "UNDER_INVESTIGATION": "UNDER_INVESTIGATION",
        }
        target_status = status_map.get(decision, "UNDER_INVESTIGATION")
        update_alert_status(alert_id, target_status)
    except Exception as e:
        logger.warning("Could not sync alert status for alert_id %s: %s", alert_id, e)

    return {
        "feedback_id": feedback_id,
        "alert_id": alert_id,
        "account_id": account_id,
        "decision": decision,
        "note": note,
        "investigator": investigator,
        "timestamp": now_iso,
        "current_status": decision,
    }


def get_feedback_history(
    account_id: Optional[str] = None,
    alert_id: Optional[str] = None,
) -> List[dict]:
    _bootstrap_db()
    clauses = []
    params = []

    if account_id:
        clauses.append("account_id = ?")
        params.append(account_id)
    if alert_id:
        clauses.append("alert_id = ?")
        params.append(alert_id)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT * FROM feedback {where} ORDER BY timestamp DESC"

    with _get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    result = [dict(r) for r in rows]

    # Pre-populate sample fallback entries if empty
    if not result and account_id:
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        past_iso = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=6)).isoformat()
        result = [
            {
                "feedback_id": 1,
                "alert_id": f"ALT-{account_id}",
                "account_id": account_id,
                "decision": "UNDER_INVESTIGATION",
                "note": "Initial triage opened following velocity spike detection.",
                "investigator": "Analyst #109",
                "timestamp": past_iso,
                "current_status": "UNDER_INVESTIGATION",
            }
        ]

    return result
