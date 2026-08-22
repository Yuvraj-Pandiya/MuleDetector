"""
app/services/alert_generator.py
================================
Prioritized Risk-Based Alert Engine for MuleDetector.

Generates and persists risk alerts from scored account DataFrames into SQLite (`alerts.db`).

Each alert contains 10 core fields:
  1. alert_id
  2. account_id
  3. risk_score (0.0 to 100.0)
  4. risk_tier ("Low", "Medium", "High", "Critical")
  5. top_reasons (List[str] plain-English signal descriptions)
  6. anomaly_score (0.0 to 1.0)
  7. network_risk (0.0 to 100.0)
  8. model_version (e.g. "v2.5.0-XGBoost")
  9. created_at (ISO 8601 UTC timestamp)
  10. status ("OPEN", "UNDER_INVESTIGATION", "CONFIRMED_MULE", "FALSE_POSITIVE", "DISMISSED")

Features:
  - Deduplication / Anti-Spam window (avoids duplicate alerts for same account within N hours)
  - Prioritized analyst queue sorting (risk_score -> severity -> network_risk -> connected_suspicious_count)
"""

from __future__ import annotations

import datetime
import hashlib
import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

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
DEFAULT_MODEL_VERSION = "v2.5.0-XGBoost"

VALID_STATUSES = {
    "OPEN",
    "UNDER_INVESTIGATION",
    "CONFIRMED_MULE",
    "FALSE_POSITIVE",
    "DISMISSED",
}

SEVERITY_RANK = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
}


# ---------------------------------------------------------------------------
# DB Bootstrap & Migration
# ---------------------------------------------------------------------------

def _bootstrap_db() -> None:
    """Create or upgrade the SQLite alerts table with all required fields."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id                    TEXT PRIMARY KEY,
                account_id                  TEXT NOT NULL,
                risk_score                  REAL NOT NULL,
                risk_tier                   TEXT NOT NULL,
                severity                    TEXT NOT NULL,
                summary                     TEXT NOT NULL,
                top_features                TEXT NOT NULL,
                top_reasons                 TEXT NOT NULL,
                anomaly_score               REAL NOT NULL DEFAULT 0.0,
                network_risk                REAL NOT NULL DEFAULT 0.0,
                connected_suspicious_count  INTEGER NOT NULL DEFAULT 0,
                model_version               TEXT NOT NULL DEFAULT 'v2.5.0-XGBoost',
                status                      TEXT NOT NULL DEFAULT 'OPEN',
                created_at                  TEXT NOT NULL,
                updated_at                  TEXT NOT NULL
            )
            """
        )

        # Migrate schema dynamically for pre-existing SQLite database files
        migrations = [
            "ALTER TABLE alerts ADD COLUMN top_reasons TEXT NOT NULL DEFAULT '[]'",
            "ALTER TABLE alerts ADD COLUMN anomaly_score REAL NOT NULL DEFAULT 0.0",
            "ALTER TABLE alerts ADD COLUMN network_risk REAL NOT NULL DEFAULT 0.0",
            "ALTER TABLE alerts ADD COLUMN connected_suspicious_count INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE alerts ADD COLUMN model_version TEXT NOT NULL DEFAULT 'v2.5.0-XGBoost'",
        ]
        for mig_sql in migrations:
            try:
                conn.execute(mig_sql)
            except sqlite3.OperationalError:
                pass  # Column already exists

        conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status   ON alerts(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_account  ON alerts(account_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_risk     ON alerts(risk_score)")


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
    if risk_score >= 85.0:
        return "CRITICAL"
    elif risk_score >= 70.0:
        return "HIGH"
    elif risk_score >= 30.0:
        return "MEDIUM"
    return "LOW"


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    try:
        d["top_features"] = json.loads(d.get("top_features", "[]"))
    except (ValueError, TypeError):
        d["top_features"] = []

    try:
        d["top_reasons"] = json.loads(d.get("top_reasons", "[]"))
    except (ValueError, TypeError):
        d["top_reasons"] = d["top_features"]

    d["risk_score"] = float(d.get("risk_score", 0.0))
    d["anomaly_score"] = float(d.get("anomaly_score", 0.0))
    d["network_risk"] = float(d.get("network_risk", 0.0))
    d["connected_suspicious_count"] = int(d.get("connected_suspicious_count", 0))
    d["status"] = str(d.get("status", "OPEN")).upper()
    d["severity"] = str(d.get("severity", "HIGH")).upper()
    d["risk_tier"] = str(d.get("risk_tier", "HIGH")).upper()
    d["model_version"] = str(d.get("model_version", DEFAULT_MODEL_VERSION))

    return d


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_alerts(
    scored_df: pd.DataFrame,
    threshold: float = 30.0,
    dedup_window_hours: float = 24.0,
    model_version: str = DEFAULT_MODEL_VERSION,
) -> List[Dict[str, Any]]:
    """
    Generate prioritized risk-based alerts and persist them to SQLite.

    Parameters
    ----------
    scored_df : pd.DataFrame
        Output of risk_scorer.score_accounts() — must contain columns:
        account_id, risk_score, risk_tier. Optional: anomaly_score, network_risk_score, top_features.
    threshold : float
        Minimum risk_score to trigger an alert (default 30.0).
    dedup_window_hours : float
        Anti-spam time window in hours to prevent duplicate alerts for the same account (default 24h).
    model_version : str
        ML model version tag.

    Returns
    -------
    List[Dict[str, Any]]
        List of generated or updated alert records.
    """
    _bootstrap_db()

    if scored_df.empty:
        logger.info("[AlertEngine] generate_alerts: empty scored DataFrame.")
        return []

    # Handle threshold scaling (if passed as 0.30 instead of 30.0)
    thresh_val = threshold * 100.0 if threshold <= 1.0 else threshold
    flagged = scored_df[scored_df["risk_score"] >= thresh_val].copy()

    if flagged.empty:
        logger.info("[AlertEngine] generate_alerts: no accounts at or above risk threshold %.1f", thresh_val)
        return []

    now_dt = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now_dt.isoformat()
    dedup_cutoff_dt = now_dt - datetime.timedelta(hours=dedup_window_hours)

    result_alerts: List[Dict[str, Any]] = []

    with _get_conn() as conn:
        for _, row in flagged.iterrows():
            account_id = str(row["account_id"])
            risk_score = round(float(row["risk_score"]), 1)
            risk_tier = str(row["risk_tier"]).upper()
            sev = _severity(risk_score)

            anomaly_sc = round(float(row.get("anomaly_score", risk_score / 100.0 * 0.85)), 4)
            net_risk = round(float(row.get("network_risk_score", row.get("network_risk", min(100.0, risk_score * 1.02)))), 1)

            # Top Reasons / Features
            top_feats = row.get("top_features", [])
            if isinstance(top_feats, list):
                top_features_list = [str(f) for f in top_feats]
            else:
                top_features_list = ["high risk score"]

            top_reasons_list = row.get("top_reasons", top_features_list)
            if not isinstance(top_reasons_list, list):
                top_reasons_list = top_features_list

            conn_susp_cnt = int(row.get("unique_counterparties", row.get("out_degree", 3))) if risk_score >= 60 else 0
            summary_text = (
                f"Account {account_id} flagged with risk score {risk_score:.1f} [{risk_tier}]. "
                f"Top signals: {', '.join(top_features_list[:2])}."
            )

            # --- Anti-Spam / De-duplication Check ---
            existing_row = conn.execute(
                """
                SELECT * FROM alerts
                WHERE account_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (account_id,),
            ).fetchone()

            is_duplicate = False
            if existing_row:
                ex_dt_str = existing_row["created_at"]
                try:
                    ex_dt = datetime.datetime.fromisoformat(ex_dt_str)
                    if ex_dt.tzinfo is None:
                        ex_dt = ex_dt.replace(tzinfo=datetime.timezone.utc)
                    if ex_dt >= dedup_cutoff_dt:
                        is_duplicate = True
                except Exception:
                    pass

            if is_duplicate and existing_row:
                # Update existing alert (preserve status)
                alert_id = existing_row["alert_id"]
                current_status = existing_row["status"]

                conn.execute(
                    """
                    UPDATE alerts SET
                        risk_score                  = ?,
                        risk_tier                   = ?,
                        severity                    = ?,
                        summary                     = ?,
                        top_features                = ?,
                        top_reasons                 = ?,
                        anomaly_score               = ?,
                        network_risk                = ?,
                        connected_suspicious_count  = ?,
                        model_version               = ?,
                        updated_at                  = ?
                    WHERE alert_id = ?
                    """,
                    (
                        risk_score, risk_tier, sev, summary_text,
                        json.dumps(top_features_list), json.dumps(top_reasons_list),
                        anomaly_sc, net_risk, conn_susp_cnt, model_version,
                        now_iso, alert_id,
                    ),
                )

                result_alerts.append({
                    "alert_id": alert_id,
                    "account_id": account_id,
                    "risk_score": risk_score,
                    "risk_tier": risk_tier,
                    "severity": sev,
                    "summary": summary_text,
                    "top_features": top_features_list,
                    "top_reasons": top_reasons_list,
                    "anomaly_score": anomaly_sc,
                    "network_risk": net_risk,
                    "connected_suspicious_count": conn_susp_cnt,
                    "model_version": model_version,
                    "status": current_status,
                    "created_at": existing_row["created_at"],
                    "updated_at": now_iso,
                })
            else:
                # Insert brand new alert record
                alert_id = _make_alert_id(f"{account_id}-{now_iso}")

                conn.execute(
                    """
                    INSERT INTO alerts
                        (alert_id, account_id, risk_score, risk_tier, severity,
                         summary, top_features, top_reasons, anomaly_score, network_risk,
                         connected_suspicious_count, model_version, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)
                    """,
                    (
                        alert_id, account_id, risk_score, risk_tier, sev,
                        summary_text, json.dumps(top_features_list), json.dumps(top_reasons_list),
                        anomaly_sc, net_risk, conn_susp_cnt, model_version, now_iso, now_iso,
                    ),
                )

                result_alerts.append({
                    "alert_id": alert_id,
                    "account_id": account_id,
                    "risk_score": risk_score,
                    "risk_tier": risk_tier,
                    "severity": sev,
                    "summary": summary_text,
                    "top_features": top_features_list,
                    "top_reasons": top_reasons_list,
                    "anomaly_score": anomaly_sc,
                    "network_risk": net_risk,
                    "connected_suspicious_count": conn_susp_cnt,
                    "model_version": model_version,
                    "status": "OPEN",
                    "created_at": now_iso,
                    "updated_at": now_iso,
                })

    logger.info("[AlertEngine] generate_alerts: processed %d alerts.", len(result_alerts))
    return result_alerts


def create_alert(
    account_id: str,
    risk_score: float,
    risk_tier: str,
    summary: str,
    top_features: List[str] | None = None,
    top_reasons: List[str] | None = None,
    anomaly_score: float = 0.0,
    network_risk: float = 0.0,
    connected_suspicious_count: int = 0,
    model_version: str = DEFAULT_MODEL_VERSION,
    dedup_window_hours: float = 24.0,
) -> Dict[str, Any]:
    """Create or update a single alert record in SQLite alerts table."""
    df_row = pd.DataFrame([{
        "account_id": account_id,
        "risk_score": risk_score,
        "risk_tier": risk_tier,
        "top_features": top_features or [],
        "top_reasons": top_reasons or top_features or [],
        "anomaly_score": anomaly_score,
        "network_risk_score": network_risk,
        "unique_counterparties": connected_suspicious_count,
    }])
    alerts = generate_alerts(df_row, threshold=0.0, dedup_window_hours=dedup_window_hours, model_version=model_version)
    return alerts[0] if alerts else {}


def get_alerts(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    risk_tier: Optional[str] = None,
    sort_by: str = "prioritized",
) -> List[Dict[str, Any]]:
    """
    Query persisted alerts with filters and prioritized analyst queue sorting.

    Sort order when sort_by='prioritized':
      1. risk_score DESC
      2. severity DESC (CRITICAL > HIGH > MEDIUM > LOW)
      3. network_risk DESC
      4. connected_suspicious_count DESC
    """
    _bootstrap_db()

    clauses: List[str] = []
    params: List[str] = []

    if severity is not None and severity.upper() != "ALL":
        clauses.append("severity = ?")
        params.append(severity.upper())

    if status is not None and status.upper() != "ALL":
        clauses.append("status = ?")
        params.append(status.upper())

    if risk_tier is not None and risk_tier.upper() != "ALL":
        clauses.append("risk_tier = ?")
        params.append(risk_tier.upper())

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

    sql = f"SELECT * FROM alerts {where}"

    with _get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    alert_dicts = [_row_to_dict(r) for r in rows]

    # Prioritized Analyst Queue Sorting
    if sort_by in ("prioritized", "risk_desc"):
        alert_dicts.sort(
            key=lambda x: (
                x["risk_score"],
                SEVERITY_RANK.get(x["severity"], 1),
                x["network_risk"],
                x["connected_suspicious_count"],
                x["created_at"],
            ),
            reverse=True,
        )
    elif sort_by == "risk_asc":
        alert_dicts.sort(key=lambda x: x["risk_score"])
    elif sort_by == "oldest":
        alert_dicts.sort(key=lambda x: x["created_at"])
    elif sort_by == "newest":
        alert_dicts.sort(key=lambda x: x["created_at"], reverse=True)

    return alert_dicts


def update_alert_status(alert_id: str, new_status: str) -> Dict[str, Any]:
    """
    Update the status of a single alert.

    Parameters
    ----------
    alert_id : str
        Target alert ID.
    new_status : str
        Must be one of OPEN, UNDER_INVESTIGATION, CONFIRMED_MULE, FALSE_POSITIVE, DISMISSED.

    Returns
    -------
    Dict[str, Any]
        Updated alert dictionary record.
    """
    st_upper = new_status.upper()
    if st_upper not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{new_status}'. Must be one of: {sorted(VALID_STATUSES)}"
        )

    _bootstrap_db()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    with _get_conn() as conn:
        cur = conn.execute(
            "UPDATE alerts SET status = ?, updated_at = ? WHERE alert_id = ?",
            (st_upper, now_iso, alert_id),
        )
        if cur.rowcount == 0:
            raise KeyError(f"alert_id '{alert_id}' not found.")

        row = conn.execute(
            "SELECT * FROM alerts WHERE alert_id = ?", (alert_id,)
        ).fetchone()

    return _row_to_dict(row)
