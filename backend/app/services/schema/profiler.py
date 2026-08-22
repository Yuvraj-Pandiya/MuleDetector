"""
app/services/schema/profiler.py
================================
CSV Profiling Service for MuleDetector.

Performs memory-safe column-level data profiling using header + representative sample.
For each column determines:
  - original_name
  - normalized_name
  - inferred_type
  - null_percentage
  - unique_count & unique_percentage
  - sample_values
  - numeric_compatibility_pct
  - datetime_compatibility_pct
  - is_integer_step (PaySim step mode check)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Sample size for memory-safe profiling
PROFILING_SAMPLE_ROWS = 1000


def normalize_header_name(header: str) -> str:
    """Normalize a column header name (lowercase, strip, replace spaces/hyphens with underscores)."""
    if not isinstance(header, str):
        return ""
    clean = header.strip().lower()
    for char in ["-", " ", ".", "/"]:
        clean = clean.replace(char, "_")
    while "__" in clean:
        clean = clean.replace("__", "_")
    return clean


def profile_column(series: pd.Series, col_name: str) -> Dict[str, Any]:
    """Profile a single pandas Series from a representative sample."""
    total_len = len(series)
    if total_len == 0:
        return {
            "source_column": col_name,
            "normalized_name": normalize_header_name(col_name),
            "inferred_type": "string",
            "null_count": 0,
            "null_percentage": 0.0,
            "unique_count": 0,
            "unique_percentage": 0.0,
            "sample_values": [],
            "numeric_compatibility_pct": 0.0,
            "datetime_compatibility_pct": 0.0,
            "is_integer_step": False,
        }

    null_count = int(series.isna().sum())
    null_pct = round((null_count / total_len) * 100.0, 2)
    non_nulls = series.dropna().astype(str).str.strip()
    non_null_count = len(non_nulls)

    unique_cnt = int(series.nunique(dropna=True))
    unique_pct = round((unique_cnt / max(non_null_count, 1)) * 100.0, 2)

    # Sample values (up to 5 distinct non-null strings)
    sample_vals = non_nulls.drop_duplicates().head(5).tolist()

    # 1. Numeric compatibility check
    numeric_parsed = pd.to_numeric(non_nulls, errors="coerce")
    numeric_valid = int(numeric_parsed.notna().sum())
    numeric_pct = round((numeric_valid / max(non_null_count, 1)) * 100.0, 2)

    # PaySim integer step check (e.g., 1, 2, 3, ... up to 744)
    is_step = False
    if numeric_pct > 95.0 and non_null_count > 0:
        num_vals = numeric_parsed.dropna()
        if (num_vals >= 0).all() and (num_vals == num_vals.astype(int)).all() and num_vals.max() <= 10000:
            if col_name.lower() in ("step", "hour", "hours", "time_step"):
                is_step = True

    # 2. Datetime compatibility check
    datetime_pct = 0.0
    if not is_step:
        # Avoid treating simple integer/float values as timestamps unless explicitly ISO/date formatted
        dt_candidates = non_nulls[~non_nulls.str.match(r"^\d{1,6}$")] if non_null_count > 0 else non_nulls
        if not dt_candidates.empty:
            dt_parsed = pd.to_datetime(dt_candidates, errors="coerce", format="ISO8601")
            dt_valid = int(dt_parsed.notna().sum())
            datetime_pct = round((dt_valid / max(len(dt_candidates), 1)) * 100.0, 2)
            if datetime_pct == 0.0:
                # Try generic datetime parsing
                dt_parsed_gen = pd.to_datetime(dt_candidates, errors="coerce")
                datetime_pct = round((int(dt_parsed_gen.notna().sum()) / max(len(dt_candidates), 1)) * 100.0, 2)

    # 3. Infer data type
    if is_step:
        inferred_type = "integer_step"
    elif datetime_pct >= 80.0:
        inferred_type = "datetime"
    elif numeric_pct >= 80.0:
        inferred_type = "numeric"
    else:
        inferred_type = "string"

    return {
        "source_column": col_name,
        "normalized_name": normalize_header_name(col_name),
        "inferred_type": inferred_type,
        "null_count": null_count,
        "null_percentage": null_pct,
        "unique_count": unique_cnt,
        "unique_percentage": unique_pct,
        "sample_values": sample_vals,
        "numeric_compatibility_pct": numeric_pct,
        "datetime_compatibility_pct": datetime_pct,
        "is_integer_step": is_step,
    }


def profile_csv(csv_path: Union[str, Path], sample_rows: int = PROFILING_SAMPLE_ROWS) -> Dict[str, Any]:
    """
    Profile a CSV dataset from disk safely using chunked/sample reading.

    Returns dictionary with total_rows, columns profile list, and raw header list.
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    # Read sample rows for fast memory-safe profiling
    sample_df = pd.read_csv(csv_path, nrows=sample_rows)
    raw_columns = sample_df.columns.tolist()

    # Estimate total rows efficiently (C-level binary chunk counting for large files)
    total_rows = len(sample_df)
    if total_rows == sample_rows:
        try:
            with csv_path.open("rb") as f:
                total_rows = max(0, sum(chunk.count(b"\n") for chunk in iter(lambda: f.read(1024 * 1024), b"")) - 1)
        except Exception:
            file_size_bytes = csv_path.stat().st_size
            total_rows = int(file_size_bytes / 85)

    col_profiles = [profile_column(sample_df[col], col) for col in raw_columns]

    return {
        "file_name": csv_path.name,
        "total_rows_estimated": total_rows,
        "sample_rows_analyzed": len(sample_df),
        "total_columns": len(raw_columns),
        "raw_headers": raw_columns,
        "column_profiles": col_profiles,
    }
