"""
app/services/data_loader.py
---------------------------
Centralised CSV ingestion and validation for MuleDetector.
"""
from __future__ import annotations

from pathlib import Path
from typing import Union

import pandas as pd

REQUIRED_COLUMNS: list[str] = [
    "transaction_id",
    "timestamp",
    "sender_account_id",
    "receiver_account_id",
    "amount",
    "transaction_type",
]


def load_transactions(csv_path: Union[str, Path]) -> pd.DataFrame:
    """
    Read a transaction CSV, validate required columns, parse timestamps.

    Parameters
    ----------
    csv_path : str | Path
        Path to the CSV file.

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame with ``timestamp`` as ``datetime64[ns]``.

    Raises
    ------
    FileNotFoundError
        If *csv_path* does not exist.
    ValueError
        If any required columns are absent (message lists every missing column).
    """
    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"Transaction file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    # --- column validation ---
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"CSV is missing required column(s): {', '.join(missing)}"
        )

    # --- timestamp parsing ---
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=False)

    # --- basic type coercion ---
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    return df
