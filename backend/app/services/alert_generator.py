"""
app/services/alert_generator.py
================================
Generate and persist risk alerts from a scored DataFrame.

Public API
----------
generate_alerts(scored_df, threshold=0.7) -> list[dict]
    Filters accounts with risk_score > threshold, assigns alert metadata,
    and upserts rows into the SQLite `alerts` table.
    Returns the list of newly inserted alert dicts.

get_alerts(severity=None, status=None) -> list[dict]
    Query the alerts table with optional filters.

update_alert_status(alert_id, new_status) -> dict
    Update a single alert's status. Raises KeyError if not found.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = _DATA_DIR / "alerts.db"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CRITICAL_THRESHOLD = 85.0   # risk_score > 85.0 → Critical
HIGH_THRESHOLD = 70.0       # risk_score > 70.0 → High

VALID_STATUSES = {
    "OPEN",
    "UNDER_INVESTIGATION",
    "CONFIRMED_MULE",
    "FALSE_POSITIVE",
    "DISMISSED",
}



# ---------------------------------------------------------------------------
# DB bootstrap
# ---------------------------------------------------------------------------

def _bootstrap_db() -> None:
    """Create the alerts table if it doesn't already exist."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id        TEXT PRIMARY KEY,
                account_id      TEXT NOT NULL,
                risk_score      REAL NOT NULL,
                risk_tier       TEXT NOT NULL,
                severity        TEXT NOT NULL,
                summary         TEXT NOT NULL,
                top_features    TEXT NOT NULL,   -- JSON array stored as string
                status          TEXT NOT NULL DEFAULT 'OPEN',
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_alerts_status   ON alerts(status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_alerts_account  ON alerts(account_id)"
        )


@contextmanager
def _get_conn() -> Generator[sqlite3.Connection, None, None]:
    """Yield a SQLite connection with WAL mode and row_factory set."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_alert_id(account_id: str) -> str:
    """Deterministic alert_id = 'ALT-' + first 8 hex chars of SHA256(account_id)."""
    digest = hashlib.sha256(account_id.encode()).hexdigest()[:8]
    return f"ALT-{digest.upper()}"


def _severity(risk_score: float) -> str:
    return "Critical" if risk_score > CRITICAL_THRESHOLD else "High"


def _build_summary(account_id: str, risk_score: float, top_features: list[str]) -> str:
    feat_str = ", ".join(top_features[:3]) if top_features else "unknown"
    return (
        f"Account {account_id} flagged with risk score {risk_score:.3f}. "
        f"Top contributing signals: {feat_str}."
    )


def _row_to_dict(row: sqlite3.Row) -> dict:
    import json
    d = dict(row)
    try:
        d["top_features"] = json.loads(d["top_features"])
    except (ValueError, TypeError):
        d["top_features"] = []
    return d


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_alerts(
    scored_df: pd.DataFrame,
    threshold: float = 0.7,
) -> list[dict]:
    """Filter scored accounts above threshold and persist alerts to SQLite.

    Parameters
    ----------
    scored_df:
        Output of risk_scorer.score_accounts() — must have columns:
        account_id, risk_score, risk_tier, top_features.
    threshold:
        Minimum risk_score to trigger an alert. Default 0.7.

    Returns
    -------
    list[dict]
        All alerts upserted in this call (including pre-existing ones
        for the same account_id that were updated).
    """
    import json

    _bootstrap_db()

    high_risk = scored_df[scored_df["risk_score"] > threshold].copy()
    if high_risk.empty:
        logger.info("generate_alerts: no accounts above threshold %.2f", threshold)
        return []

    now_iso = datetime.now(timezone.utc).isoformat()
    inserted: list[dict] = []

    with _get_conn() as conn:
        for _, row in high_risk.iterrows():
            account_id = str(row["account_id"])
            risk_score = float(row["risk_score"])
            risk_tier = str(row["risk_tier"])
            top_features = list(row["top_features"])

            alert_id = _make_alert_id(account_id)
            severity = _severity(risk_score)
            summary = _build_summary(account_id, risk_score, top_features)

            # Upsert: on conflict update risk_score/severity/summary/updated_at
            # but preserve status (don't reset REVIEWED → OPEN on re-run)
            conn.execute(
                """
                INSERT INTO alerts
                    (alert_id, account_id, risk_score, risk_tier, severity,
                     summary, top_features, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)
                ON CONFLICT(alert_id) DO UPDATE SET
                    risk_score  = excluded.risk_score,
                    risk_tier   = excluded.risk_tier,
                    severity    = excluded.severity,
                    summary     = excluded.summary,
                    top_features= excluded.top_features,
                    updated_at  = excluded.updated_at
                """,
                (
                    alert_id, account_id, risk_score, risk_tier, severity,
                    summary, json.dumps(top_features), now_iso, now_iso,
                ),
            )

            inserted.append(
                {
                    "alert_id": alert_id,
                    "account_id": account_id,
                    "risk_score": round(risk_score, 4),
                    "risk_tier": risk_tier,
                    "severity": severity,
                    "summary": summary,
                    "top_features": top_features,
                    "status": "OPEN",
                    "created_at": now_iso,
                    "updated_at": now_iso,
                }
            )

    logger.info(
        "generate_alerts: upserted %d alerts (threshold=%.2f)  "
        "Critical=%d  High=%d",
        len(inserted),
        threshold,
        sum(1 for a in inserted if a["severity"] == "Critical"),
        sum(1 for a in inserted if a["severity"] == "High"),
    )
    return inserted


def get_alerts(
    severity: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """Query persisted alerts with optional severity/status filters.

    Parameters
    ----------
    severity : str | None
        If given, filter to 'High' or 'Critical'.
    status : str | None
        If given, filter to 'OPEN', 'REVIEWED', or 'DISMISSED'.

    Returns
    -------
    list[dict]
        Alerts sorted by risk_score descending.
    """
    _bootstrap_db()

    clauses: list[str] = []
    params: list[str] = []

    if severity is not None:
        clauses.append("severity = ?")
        params.append(severity)
    if status is not None:
        clauses.append("status = ?")
        params.append(status)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT * FROM alerts {where} ORDER BY risk_score DESC"

    with _get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [_row_to_dict(r) for r in rows]


def update_alert_status(alert_id: str, new_status: str) -> dict:
    """Update the status of a single alert.

    Parameters
    ----------
    alert_id : str
        The alert to update.
    new_status : str
        Must be one of OPEN, REVIEWED, DISMISSED.

    Returns
    -------
    dict
        The updated alert record.

    Raises
    ------
    ValueError
        If new_status is not a valid status.
    KeyError
        If alert_id is not found.
    """
    if new_status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{new_status}'. Must be one of: "
            + ", ".join(sorted(VALID_STATUSES))
        )

    _bootstrap_db()
    now_iso = datetime.now(timezone.utc).isoformat()

    with _get_conn() as conn:
        cur = conn.execute(
            "UPDATE alerts SET status = ?, updated_at = ? WHERE alert_id = ?",
            (new_status, now_iso, alert_id),
        )
        if cur.rowcount == 0:
            raise KeyError(f"alert_id '{alert_id}' not found.")

        row = conn.execute(
            "SELECT * FROM alerts WHERE alert_id = ?", (alert_id,)
        ).fetchone()

    return _row_to_dict(row)
