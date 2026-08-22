"""
generate_sample.py
------------------
Generates a small synthetic transaction CSV for testing purposes.

Usage:
    python scripts/generate_sample.py --output app/data/sample_transactions.csv \
        --n-accounts 50 --n-transactions 500 --seed 42
"""
from __future__ import annotations

import argparse
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd


TRANSACTION_TYPES = ["TRANSFER", "PAYMENT", "CASH_IN", "CASH_OUT"]


def generate_sample(
    n_accounts: int = 50,
    n_transactions: int = 500,
    seed: int = 42,
) -> pd.DataFrame:
    rng = random.Random(seed)

    account_ids = [f"ACC{str(i).zfill(5)}" for i in range(n_accounts)]

    base_time = datetime(2024, 1, 1, 0, 0, 0)
    rows = []

    for i in range(n_transactions):
        sender = rng.choice(account_ids)
        receiver = rng.choice([a for a in account_ids if a != sender])
        rows.append(
            {
                "transaction_id": str(uuid.UUID(int=rng.getrandbits(128))),
                "timestamp": base_time + timedelta(minutes=rng.randint(0, 60 * 24 * 30)),
                "sender_account_id": sender,
                "receiver_account_id": receiver,
                "amount": round(rng.uniform(10, 10_000), 2),
                "transaction_type": rng.choice(TRANSACTION_TYPES),
            }
        )

    df = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a synthetic transaction CSV.")
    parser.add_argument("--output", default="app/data/sample_transactions.csv")
    parser.add_argument("--n-accounts", type=int, default=50)
    parser.add_argument("--n-transactions", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = generate_sample(args.n_accounts, args.n_transactions, args.seed)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"[generate_sample] wrote {len(df)} rows -> {out}")


if __name__ == "__main__":
    main()
