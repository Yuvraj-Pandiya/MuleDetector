"""
scripts/test_b5_acceptance.py
==============================
Programmatic acceptance checks for Prompt B5.

Runs the full mock-data pipeline end-to-end and verifies:
  1. train -> risk-scores -> alerts/generate -> dashboard-summary
     all succeed; print each response status.
  2. /explain/{nonexistent_id} returns a clean 4xx JSON error, not 500.

Prerequisites:
  - scripts/generate_mock_features.py has been run (mock_features.csv exists)
  - uvicorn is running on 127.0.0.1:8000
"""

from __future__ import annotations

import json
import sys

import requests

BASE = "http://127.0.0.1:8000"


def check(cond: bool, msg: str) -> None:
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {msg}")
    if not cond:
        sys.exit(1)


def step(label: str, method: str, path: str, **kwargs) -> requests.Response:
    """Fire a request, print a one-liner, return the response."""
    url = f"{BASE}{path}"
    resp = getattr(requests, method)(url, timeout=90, **kwargs)
    print(f"  {method.upper():5}  {path:45}  ->  HTTP {resp.status_code}")
    return resp


def main() -> None:
    print("=" * 65)
    print("B5 Acceptance Tests -- Full Pipeline Run")
    print("=" * 65)

    # ------------------------------------------------------------------
    # 1. End-to-end pipeline
    # ------------------------------------------------------------------
    print("\n[1] Full pipeline: train -> risk-scores -> alerts -> dashboard")

    # --- train ---
    r = step("post", "post", "/train")
    check(r.status_code == 200, f"POST /train  HTTP 200 (got {r.status_code})")
    metrics = r.json()["metrics"]
    check(metrics.get("roc_auc", 0) > 0.7, f"ROC-AUC > 0.7 (got {metrics.get('roc_auc')})")

    # --- risk-scores ---
    r = step("get", "get", "/predict/risk-scores")
    check(r.status_code == 200, f"GET /predict/risk-scores  HTTP 200 (got {r.status_code})")
    scored = r.json()
    check(scored["count"] == 1000, f"1000 accounts scored (got {scored['count']})")
    scores = [a["risk_score"] for a in scored["accounts"]]
    check(
        all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1)),
        "risk_scores sorted descending",
    )

    # --- alerts/generate ---
    r = step("post", "post", "/alerts/generate")
    check(r.status_code == 200, f"POST /alerts/generate  HTTP 200 (got {r.status_code})")
    alert_payload = r.json()
    check(alert_payload["generated"] > 0, f">=1 alert generated (got {alert_payload['generated']})")

    # --- dashboard-summary ---
    r = step("get", "get", "/dashboard/summary")
    check(r.status_code == 200, f"GET /dashboard/summary  HTTP 200 (got {r.status_code})")
    dash = r.json()

    # Verify structure
    required_keys = {
        "total_accounts", "flagged_count", "risk_tier_breakdown",
        "open_alert_count", "top_10_highest_risk", "model_metrics",
    }
    check(
        required_keys.issubset(dash.keys()),
        f"Dashboard has required keys (missing: {required_keys - dash.keys()})",
    )
    check(dash["total_accounts"] == 1000, f"total_accounts=1000 (got {dash['total_accounts']})")
    check(dash["flagged_count"] > 0, f"flagged_count > 0 (got {dash['flagged_count']})")

    breakdown = dash["risk_tier_breakdown"]
    check(
        set(breakdown.keys()) == {"High", "Medium", "Low"},
        f"risk_tier_breakdown has all tiers (got {set(breakdown.keys())})",
    )
    check(
        sum(breakdown.values()) == 1000,
        f"Tier counts sum to 1000 (got {sum(breakdown.values())})",
    )
    check(
        len(dash["top_10_highest_risk"]) == 10,
        f"top_10_highest_risk has 10 entries (got {len(dash['top_10_highest_risk'])})",
    )
    check(
        dash["open_alert_count"] > 0,
        f"open_alert_count > 0 (got {dash['open_alert_count']})",
    )
    check(
        "roc_auc" in dash["model_metrics"],
        "model_metrics contains roc_auc",
    )

    print(f"\n  Dashboard snapshot:")
    print(f"    total_accounts      : {dash['total_accounts']}")
    print(f"    flagged_count       : {dash['flagged_count']}")
    print(f"    risk_tier_breakdown : {dash['risk_tier_breakdown']}")
    print(f"    open_alert_count    : {dash['open_alert_count']}")
    print(f"    model roc_auc       : {dash['model_metrics'].get('roc_auc')}")

    # ------------------------------------------------------------------
    # 2. Nonexistent account_id → clean 4xx, not 500
    # ------------------------------------------------------------------
    print("\n[2] /explain/{nonexistent_id} -> clean 4xx JSON error")

    r = step("get", "get", "/predict/explain/ACCOUNT_THAT_DOES_NOT_EXIST")
    check(
        400 <= r.status_code < 500,
        f"Status is 4xx (got {r.status_code}), not 500",
    )

    body = r.json()
    check("detail" in body, f"Response body has 'detail' key (got {list(body.keys())})")
    check(
        r.status_code != 500,
        "Not a 500 Internal Server Error (no raw traceback leaked)",
    )
    print(f"  Response: {json.dumps(body, indent=4)}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 65)
    print("ALL B5 ACCEPTANCE CHECKS PASSED")
    print("=" * 65)


if __name__ == "__main__":
    main()
