"""
scripts/test_b3_acceptance.py
==============================
Programmatic acceptance checks for Prompt B3.

Run AFTER POST /train has been called (model.pkl must exist).
Fires against the live uvicorn server on 127.0.0.1:8000.

Checks:
  1. GET /predict/risk-scores returns accounts sorted descending by risk_score.
  2. Accounts that are is_mule_pattern=1 in mock_features.csv have risk_tier
     of Medium or High (not Low).
  3. GET /predict/explain/{account_id} returns a non-empty reason string.
"""

from __future__ import annotations

import pathlib
import sys

import pandas as pd
import requests

BASE = "http://127.0.0.1:8000"
MOCK_CSV = pathlib.Path(__file__).parent.parent / "app" / "data" / "mock_features.csv"


def check(cond: bool, msg: str) -> None:
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {msg}")
    if not cond:
        sys.exit(1)


def main() -> None:
    print("=" * 60)
    print("B3 Acceptance Tests")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. GET /predict/risk-scores — sorted descending
    # ------------------------------------------------------------------
    print("\n[1] risk-scores sorted descending")
    resp = requests.get(f"{BASE}/predict/risk-scores", timeout=60)
    check(resp.status_code == 200, f"HTTP 200 (got {resp.status_code})")

    payload = resp.json()
    accounts = payload["accounts"]
    check(len(accounts) == 1000, f"Returns 1000 accounts (got {len(accounts)})")

    scores = [a["risk_score"] for a in accounts]
    sorted_desc = all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))
    check(sorted_desc, "risk_score values are sorted descending")

    # ------------------------------------------------------------------
    # 2. Known mule rows are Medium or High tier
    # ------------------------------------------------------------------
    print("\n[2] Mule accounts are Medium or High risk tier")
    df = pd.read_csv(MOCK_CSV)
    mule_ids = set(df[df["is_mule_pattern"] == 1]["account_id"].tolist())
    print(f"   Total mule accounts in CSV: {len(mule_ids)}")

    account_map = {a["account_id"]: a for a in accounts}
    wrong_tier = []
    for aid in mule_ids:
        tier = account_map.get(aid, {}).get("risk_tier", "MISSING")
        if tier not in ("Medium", "High"):
            wrong_tier.append((aid, tier))

    check(
        len(wrong_tier) == 0,
        f"All {len(mule_ids)} mule accounts are Medium/High "
        f"(violations: {wrong_tier[:5]}{'...' if len(wrong_tier) > 5 else ''})",
    )

    # ------------------------------------------------------------------
    # 3. /explain/{account_id} returns a non-empty reason
    # ------------------------------------------------------------------
    print("\n[3] explain endpoint returns non-empty reason string")
    # Pick the highest-risk account (first in sorted list)
    test_id = accounts[0]["account_id"]
    print(f"   Testing account: {test_id}")
    resp2 = requests.get(f"{BASE}/predict/explain/{test_id}", timeout=60)
    check(resp2.status_code == 200, f"HTTP 200 (got {resp2.status_code})")

    expl = resp2.json()
    check("reason" in expl, "Response contains 'reason' key")
    check(len(expl["reason"]) > 10, f"reason is non-trivial: '{expl['reason'][:80]}'")
    check(
        isinstance(expl.get("top_shap_features"), list) and len(expl["top_shap_features"]) > 0,
        "top_shap_features is a non-empty list",
    )
    print(f"   reason: {expl['reason']}")

    print("\n" + "=" * 60)
    print("ALL B3 ACCEPTANCE CHECKS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
