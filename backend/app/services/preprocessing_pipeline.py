"""
app/services/preprocessing_pipeline.py
========================================
Production-Quality Preprocessing Pipeline for Financial Transaction Data.

Maintains strict temporal order, removes exact duplicates, cleans invalid amounts
and missing entity IDs, standardizes transaction types, logs transformations,
and outputs comprehensive stats + rejected record reports.

Reusable for both training data (with labels) and inference data (unlabeled).
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import pandas as pd

from app.services.data_loader import load_transactions
from app.services.dataset_config import DatasetSchemaMapping

logger = logging.getLogger(__name__)


class TransactionPreprocessor:
    """
    Production-grade, reusable preprocessor for financial transaction data.
    """

    def __init__(
        self,
        schema_mapping: Optional[DatasetSchemaMapping] = None,
        save_report: bool = True,
        report_dir: Optional[Union[str, Path]] = None,
    ) -> None:
        self.schema_mapping = schema_mapping
        self.save_report = save_report
        if report_dir:
            self.report_dir = Path(report_dir)
        else:
            self.report_dir = Path(__file__).parent.parent / "data"

    def process(
        self,
        data_input: Union[str, Path, pd.DataFrame],
        max_rows: Optional[int] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, Any], pd.DataFrame]:
        """
        Execute full preprocessing pipeline on transaction data.

        Parameters
        ----------
        data_input : str | Path | pd.DataFrame
            Path to raw transaction CSV or pre-loaded raw DataFrame.
        max_rows : Optional[int]
            Optional row cap (useful for sampling massive datasets like PaySim).

        Returns
        -------
        Tuple[pd.DataFrame, Dict[str, Any], pd.DataFrame]
            - cleaned_df : pd.DataFrame (chronologically sorted, valid schema)
            - stats : Dict[str, Any] (transformation statistics & quality summary)
            - rejected_df : pd.DataFrame (quarantined records with rejection_reason)
        """
        t0 = time.perf_counter()
        logger.info("[Preprocessor] Starting transaction preprocessing pipeline...")

        # ------------------------------------------------------------------
        # 1. Ingest Data into Canonical Schema
        # ------------------------------------------------------------------
        if isinstance(data_input, (str, Path)):
            raw_file_name = Path(data_input).name
            df_canonical = load_transactions(
                data_input,
                schema_mapping=self.schema_mapping,
                max_rows=max_rows,
            )
        elif isinstance(data_input, pd.DataFrame):
            raw_file_name = "in_memory_dataframe"
            df_canonical = data_input.copy()
        else:
            raise TypeError(f"Unsupported input type: {type(data_input)}")

        initial_row_count = len(df_canonical)
        logger.info("[Preprocessor] Step 1: Ingested %d raw rows from '%s'", initial_row_count, raw_file_name)

        rejected_rows = []

        # ------------------------------------------------------------------
        # 2. Validate & Filter Missing Sender / Receiver Account IDs
        # ------------------------------------------------------------------
        missing_sender_mask = df_canonical["sender_account_id"].isna() | (df_canonical["sender_account_id"].astype(str).str.strip() == "")
        missing_receiver_mask = df_canonical["receiver_account_id"].isna() | (df_canonical["receiver_account_id"].astype(str).str.strip() == "")
        missing_entity_mask = missing_sender_mask | missing_receiver_mask

        if missing_entity_mask.any():
            missing_entities_df = df_canonical[missing_entity_mask].copy()
            missing_entities_df["rejection_reason"] = "MISSING_SENDER_OR_RECEIVER_ID"
            rejected_rows.append(missing_entities_df)
            df_canonical = df_canonical[~missing_entity_mask].copy()

        missing_entities_count = int(missing_entity_mask.sum())
        logger.info("[Preprocessor] Step 2: Quarantined %d rows with missing sender/receiver IDs", missing_entities_count)

        # ------------------------------------------------------------------
        # 3. Detect & Filter Invalid / Negative Transaction Amounts
        # ------------------------------------------------------------------
        invalid_amount_mask = df_canonical["amount"].isna() | (df_canonical["amount"] <= 0)

        if invalid_amount_mask.any():
            invalid_amounts_df = df_canonical[invalid_amount_mask].copy()
            invalid_amounts_df["rejection_reason"] = "INVALID_OR_NON_POSITIVE_AMOUNT"
            rejected_rows.append(invalid_amounts_df)
            df_canonical = df_canonical[~invalid_amount_mask].copy()

        invalid_amounts_count = int(invalid_amount_mask.sum())
        logger.info("[Preprocessor] Step 3: Quarantined %d rows with invalid or non-positive amounts", invalid_amounts_count)

        # ------------------------------------------------------------------
        # 4. Parse & Validate Timestamps
        # ------------------------------------------------------------------
        df_canonical["timestamp"] = pd.to_datetime(df_canonical["timestamp"], errors="coerce")
        invalid_timestamp_mask = df_canonical["timestamp"].isna()

        if invalid_timestamp_mask.any():
            invalid_ts_df = df_canonical[invalid_timestamp_mask].copy()
            invalid_ts_df["rejection_reason"] = "UNPARSEABLE_TIMESTAMP"
            rejected_rows.append(invalid_ts_df)
            df_canonical = df_canonical[~invalid_timestamp_mask].copy()

        invalid_ts_count = int(invalid_timestamp_mask.sum())
        logger.info("[Preprocessor] Step 4: Quarantined %d rows with unparseable timestamps", invalid_ts_count)

        # ------------------------------------------------------------------
        # 5. Remove Exact Duplicate Transactions
        # ------------------------------------------------------------------
        dup_subset = ["sender_account_id", "receiver_account_id", "amount", "timestamp", "transaction_type"]
        dup_subset = [c for c in dup_subset if c in df_canonical.columns]

        duplicate_mask = df_canonical.duplicated(subset=dup_subset, keep="first")
        if duplicate_mask.any():
            duplicates_df = df_canonical[duplicate_mask].copy()
            duplicates_df["rejection_reason"] = "EXACT_DUPLICATE_TRANSACTION"
            rejected_rows.append(duplicates_df)
            df_canonical = df_canonical[~duplicate_mask].copy()

        duplicate_count = int(duplicate_mask.sum())
        logger.info("[Preprocessor] Step 5: Removed %d exact duplicate transaction rows", duplicate_count)

        # ------------------------------------------------------------------
        # 6. Standardize Transaction Types
        # ------------------------------------------------------------------
        if "transaction_type" in df_canonical.columns:
            df_canonical["transaction_type"] = (
                df_canonical["transaction_type"]
                .astype(str)
                .str.strip()
                .str.upper()
                .replace({"NAN": "TRANSFER", "": "TRANSFER", "NONE": "TRANSFER"})
            )
        else:
            df_canonical["transaction_type"] = "TRANSFER"

        logger.info("[Preprocessor] Step 6: Standardized transaction types")

        # ------------------------------------------------------------------
        # 7. Preserve Transaction Chronology (Strict Timestamp Sort)
        # ------------------------------------------------------------------
        df_canonical = df_canonical.sort_values("timestamp", ascending=True).reset_index(drop=True)
        logger.info("[Preprocessor] Step 7: Chronologically sorted transactions by timestamp")

        # ------------------------------------------------------------------
        # 8. Assemble Rejected Record Report
        # ------------------------------------------------------------------
        if rejected_rows:
            rejected_df = pd.concat(rejected_rows, ignore_index=True)
        else:
            rejected_df = pd.DataFrame(columns=list(df_canonical.columns) + ["rejection_reason"])

        final_row_count = len(df_canonical)
        rejected_total = len(rejected_df)
        elapsed_seconds = round(time.perf_counter() - t0, 3)

        # ------------------------------------------------------------------
        # 9. Compute Transformation Statistics
        # ------------------------------------------------------------------
        type_distribution = (
            df_canonical["transaction_type"].value_counts().to_dict()
            if "transaction_type" in df_canonical.columns
            else {}
        )

        date_range_info = {}
        if not df_canonical.empty:
            date_range_info = {
                "start": str(df_canonical["timestamp"].min()),
                "end": str(df_canonical["timestamp"].max()),
                "days_span": round((df_canonical["timestamp"].max() - df_canonical["timestamp"].min()).total_seconds() / 86400, 2),
            }

        stats: Dict[str, Any] = {
            "source_file": raw_file_name,
            "initial_row_count": initial_row_count,
            "final_cleaned_row_count": final_row_count,
            "total_rejected_row_count": rejected_total,
            "rejections_breakdown": {
                "missing_entities": missing_entities_count,
                "invalid_amounts": invalid_amounts_count,
                "unparseable_timestamps": invalid_ts_count,
                "duplicates": duplicate_count,
            },
            "date_range": date_range_info,
            "unique_senders": df_canonical["sender_account_id"].nunique() if not df_canonical.empty else 0,
            "unique_receivers": df_canonical["receiver_account_id"].nunique() if not df_canonical.empty else 0,
            "transaction_type_distribution": type_distribution,
            "execution_time_seconds": elapsed_seconds,
        }

        if "is_mule_pattern" in df_canonical.columns:
            mule_counts = df_canonical["is_mule_pattern"].value_counts().to_dict()
            stats["mule_label_distribution"] = {
                "legitimate": mule_counts.get(0, 0),
                "mule": mule_counts.get(1, 0),
                "mule_rate_pct": round((mule_counts.get(1, 0) / max(final_row_count, 1)) * 100, 3),
            }

        logger.info(
            "[Preprocessor] Complete in %.3fs | Final cleaned: %d | Rejected: %d",
            elapsed_seconds,
            final_row_count,
            rejected_total,
        )

        # ------------------------------------------------------------------
        # 10. Persist Report to File (if requested)
        # ------------------------------------------------------------------
        if self.save_report:
            try:
                self.report_dir.mkdir(parents=True, exist_ok=True)
                report_file = self.report_dir / "preprocessing_report.json"
                with open(report_file, "w", encoding="utf-8") as fh:
                    json.dump(stats, fh, indent=2)
                logger.info("[Preprocessor] Saved report -> '%s'", report_file)
            except Exception as exc:
                logger.warning("[Preprocessor] Failed to save report JSON: %s", exc)

        return df_canonical, stats, rejected_df


def preprocess_transactions(
    data_input: Union[str, Path, pd.DataFrame],
    schema_mapping: Optional[DatasetSchemaMapping] = None,
    max_rows: Optional[int] = None,
    save_report: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, Any], pd.DataFrame]:
    """
    Functional wrapper for TransactionPreprocessor.process().
    """
    preprocessor = TransactionPreprocessor(
        schema_mapping=schema_mapping,
        save_report=save_report,
    )
    return preprocessor.process(data_input, max_rows=max_rows)
