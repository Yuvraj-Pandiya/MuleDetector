"""
inject_mule_patterns.py
-----------------------
Injects realistic money-mule transaction patterns into an existing
transaction DataFrame and labels them.

Expected input columns
----------------------
transaction_id       str   – unique ID per transaction
timestamp            datetime-like (parsed automatically)
sender_account_id    str
receiver_account_id  str
amount               float
transaction_type     str   – e.g. TRANSFER, PAYMENT, CASH_IN, CASH_OUT

Output
------
The original DataFrame plus injected rows, sorted by timestamp.
New column ``is_mule_pattern`` (int 0/1) marks every injected row 1.

Usage
-----
    python scripts/inject_mule_patterns.py \
        --input  app/data/sample_transactions.csv \
        --output app/data/mule_injected.csv \
        --n-accounts 200 \
        --seed 42
"""
from __future__ import annotations

import argparse
import random
import uuid
from datetime import timedelta
from pathlib import Path
from typing import List

import pandas as pd


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _new_txn_id(rng: random.Random) -> str:
    """Return a UUID-style transaction ID."""
    return str(uuid.UUID(int=rng.getrandbits(128)))


def _random_external_sender(existing_ids: List[str], rng: random.Random) -> str:
    """Pick a random sender that *may* be outside the main account pool."""
    if rng.random() < 0.4:
        # 40 % of the time use a completely new external account
        return f"EXT{rng.randint(100_000, 999_999)}"
    return rng.choice(existing_ids)


def _inject_account(
    mule_id: str,
    existing_ids: List[str],
    rng: random.Random,
    base_ts: "pd.Timestamp",
) -> List[dict]:
    """
    Build injected rows for a single mule account.

    Pattern
    -------
    1. 1–3 large inbound TRANSFER transactions.
    2. For each inbound: 1–4 outbound transactions within 5–45 min,
       either fanning out (multiple receivers) or a single layering hop.
    3. Optional CASH_OUT for a fraction of funds.
    """
    rows: List[dict] = []

    n_inbound = rng.randint(1, 3)

    for _ in range(n_inbound):
        # --- inbound ---
        in_amount = round(rng.uniform(50_000, 500_000), 2)
        in_ts = base_ts + timedelta(
            minutes=rng.randint(0, 60 * 24 * 30)  # spread over 30 days
        )
        sender = _random_external_sender(existing_ids, rng)
        rows.append(
            {
                "transaction_id": _new_txn_id(rng),
                "timestamp": in_ts,
                "sender_account_id": sender,
                "receiver_account_id": mule_id,
                "amount": in_amount,
                "transaction_type": "TRANSFER",
                "is_mule_pattern": 1,
            }
        )

        # --- outbound burst ---
        n_outbound = rng.randint(1, 4)
        # fan-out vs. layering chain (50/50)
        fan_out: bool = rng.random() < 0.5

        remaining = in_amount
        receivers_used: List[str] = []

        for j in range(n_outbound):
            delay_min = rng.randint(5, 45)
            out_ts = in_ts + timedelta(minutes=delay_min * (j + 1) if not fan_out else delay_min)

            # choose a unique receiver that is not the mule itself
            pool = [a for a in existing_ids if a != mule_id and a not in receivers_used]
            if not pool:
                pool = [a for a in existing_ids if a != mule_id]
            receiver = rng.choice(pool)
            receivers_used.append(receiver)

            if j == n_outbound - 1:
                # last outbound: send all remaining (minus small float drift)
                out_amount = round(min(remaining, remaining * rng.uniform(0.85, 1.0)), 2)
            else:
                # partial forward
                out_amount = round(remaining * rng.uniform(0.2, 0.6), 2)
            remaining -= out_amount
            remaining = max(remaining, 0.0)

            rows.append(
                {
                    "transaction_id": _new_txn_id(rng),
                    "timestamp": out_ts,
                    "sender_account_id": mule_id,
                    "receiver_account_id": receiver,
                    "amount": max(out_amount, 0.01),
                    "transaction_type": "TRANSFER",
                    "is_mule_pattern": 1,
                }
            )

        # --- optional CASH_OUT ---
        if rng.random() < 0.45 and remaining > 0:
            cash_out_ts = in_ts + timedelta(minutes=rng.randint(60, 240))
            rows.append(
                {
                    "transaction_id": _new_txn_id(rng),
                    "timestamp": cash_out_ts,
                    "sender_account_id": mule_id,
                    "receiver_account_id": f"ATM{rng.randint(1000, 9999)}",
                    "amount": round(remaining * rng.uniform(0.5, 1.0), 2),
                    "transaction_type": "CASH_OUT",
                    "is_mule_pattern": 1,
                }
            )

    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def inject_mule_patterns(
    df: pd.DataFrame,
    n_accounts: int = 200,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Inject money-mule patterns into *df* and return the augmented DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Transaction data with columns:
        [transaction_id, timestamp, sender_account_id,
         receiver_account_id, amount, transaction_type]
    n_accounts : int
        Number of accounts to designate as mules.
    seed : int
        RNG seed for reproducibility.

    Returns
    -------
    pd.DataFrame
        Original rows (is_mule_pattern=0) + injected rows (is_mule_pattern=1),
        sorted by timestamp, index reset.
    """
    required_cols = {
        "transaction_id", "timestamp", "sender_account_id",
        "receiver_account_id", "amount", "transaction_type",
    }
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Input DataFrame is missing columns: {missing}")

    rng = random.Random(seed)

    # Ensure timestamp is a proper datetime
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Stamp existing rows as clean (0); preserve pre-existing label if present
    if "is_mule_pattern" not in df.columns:
        df["is_mule_pattern"] = 0
    else:
        df["is_mule_pattern"] = df["is_mule_pattern"].fillna(0).astype(int)

    # All unique account IDs in the original dataset
    all_accounts: List[str] = list(
        set(df["sender_account_id"].tolist() + df["receiver_account_id"].tolist())
    )

    # Step 1 — select n_accounts random mule accounts (seeded)
    actual_n = min(n_accounts, len(all_accounts))
    if actual_n < n_accounts:
        print(
            f"[warn] Requested {n_accounts} mule accounts but only "
            f"{len(all_accounts)} unique accounts available; using {actual_n}."
        )
    mule_accounts: List[str] = rng.sample(all_accounts, actual_n)

    base_ts = df["timestamp"].min()

    # Step 2–4 — inject rows per mule account
    injected_rows: List[dict] = []
    for mule_id in mule_accounts:
        injected_rows.extend(
            _inject_account(mule_id, all_accounts, rng, base_ts)
        )

    injected_df = pd.DataFrame(injected_rows)

    # Step 5 — combine, sort, reset index
    result = (
        pd.concat([df, injected_df], ignore_index=True)
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    # Step 6 — summary
    n_orig = len(df)
    n_injected = len(injected_df)
    n_total = len(result)
    n_mule_accounts = result.loc[result["is_mule_pattern"] == 1, "sender_account_id"].nunique()

    print("=" * 55)
    print("  inject_mule_patterns — summary")
    print("=" * 55)
    print(f"  Original rows      : {n_orig:>8,}")
    print(f"  Injected rows      : {n_injected:>8,}")
    print(f"  Expected total     : {n_orig + n_injected:>8,}")
    print(f"  Actual total       : {n_total:>8,}  {'OK' if n_total == n_orig + n_injected else 'MISMATCH'}")
    print(f"  Mule accounts      : {actual_n:>8,}")
    print(f"  Mule rows (1)      : {result['is_mule_pattern'].sum():>8,}")
    print(f"  Clean rows (0)     : {(result['is_mule_pattern'] == 0).sum():>8,}")
    print(f"  Unique mule senders: {n_mule_accounts:>8,}")
    print("=" * 55)

    assert n_total == n_orig + n_injected, (
        f"Row count mismatch: expected {n_orig + n_injected}, got {n_total}"
    )
    assert result["is_mule_pattern"].isin([0, 1]).all(), (
        "is_mule_pattern contains values other than 0/1"
    )
    assert result["is_mule_pattern"].nunique() == 2, (
        "is_mule_pattern must contain both 0 and 1"
    )

    return result


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inject money-mule transaction patterns into a CSV."
    )
    parser.add_argument(
        "--input", required=True,
        help="Path to the input transaction CSV.",
    )
    parser.add_argument(
        "--output", required=True,
        help="Path to write the augmented CSV.",
    )
    parser.add_argument(
        "--n-accounts", type=int, default=200,
        help="Number of mule accounts to inject (default: 200).",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42).",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        raise FileNotFoundError(f"Input file not found: {in_path}")

    print(f"[inject] Reading {in_path} …")
    df_in = pd.read_csv(in_path, parse_dates=["timestamp"])

    df_out = inject_mule_patterns(df_in, n_accounts=args.n_accounts, seed=args.seed)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(out_path, index=False)
    print(f"[inject] Saved {len(df_out):,} rows -> {out_path}")


if __name__ == "__main__":
    main()
