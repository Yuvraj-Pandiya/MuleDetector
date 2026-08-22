"""
app/services/schema/column_mapper.py
=====================================
Multi-Stage Column Mapping & Deterministic Confidence Scoring Engine.

Stages:
  Stage 1: Exact Normalized Header Name Match
  Stage 2: Alias Dictionary Lookup
  Stage 3: Fuzzy String Similarity (difflib SequenceMatcher)
  Stage 4: Data-Type Compatibility Verification
  Stage 5: Semantic Value-Pattern Classifier (e.g. column "value" containing "UPI" vs "1500.0")

Confidence Weighting:
  Header Similarity      : 40%
  Alias Dictionary Match : 25%
  Data-Type Compatibility: 20%
  Value-Pattern Match    : 15%

Confidence Tiers:
  >= 0.90 -> HIGH CONFIDENCE   (status: 'auto')
  0.70-0.89 -> MEDIUM CONFIDENCE (status: 'review')
  < 0.70  -> LOW CONFIDENCE    (status: 'manual')
"""

from __future__ import annotations

import difflib
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from app.services.schema.canonical_schema import (
    ALIAS_DICTIONARY,
    CANONICAL_FIELDS,
    CanonicalField,
    MANDATORY_SOURCE_FIELDS,
    REQUIRED_CANONICAL_FIELDS,
)
from app.services.schema.profiler import normalize_header_name, profile_column

logger = logging.getLogger(__name__)


@dataclass
class SingleColumnMapping:
    """Mapping decision details for a single external source column."""
    source: str
    target: Optional[str]
    confidence: float
    status: str  # 'auto', 'review', 'manual', 'unmapped'
    matched_stage: str
    inferred_type: str
    sample_values: List[str]
    candidate_targets: List[Dict[str, Any]]


@dataclass
class ColumnMappingResult:
    """Overall dataset schema mapping result."""
    status: str  # 'auto_ready', 'mapping_required'
    mappings: List[SingleColumnMapping]
    mapped_dict: Dict[str, str]  # {source_column: canonical_field_name}
    missing_required: List[str]
    unmapped_columns: List[str]
    can_train: bool
    can_predict: bool


def _calculate_header_similarity(source_norm: str, canonical_name: str) -> float:
    """Compute string similarity ratio between normalized source header and canonical field name."""
    if source_norm == canonical_name:
        return 1.0
    return round(difflib.SequenceMatcher(None, source_norm, canonical_name).ratio(), 3)


def _check_alias_match(source_norm: str, canonical_field: CanonicalField) -> Tuple[bool, float]:
    """Check if source_norm matches an explicit alias for canonical_field."""
    if source_norm == canonical_field.name:
        return True, 1.0
    if source_norm in canonical_field.aliases:
        return True, 1.0
    # Substring / split check
    for alias in canonical_field.aliases:
        if len(alias) > 3 and (alias in source_norm or source_norm in alias):
            return True, 0.85
    return False, 0.0


def _check_type_compatibility(inferred_type: str, expected_type: str) -> float:
    """Check compatibility between inferred data type and expected canonical data type."""
    if expected_type == "float" or expected_type == "integer":
        if inferred_type in ("numeric", "integer_step"):
            return 1.0
        return 0.0

    if expected_type == "datetime":
        if inferred_type in ("datetime", "integer_step"):
            return 1.0
        return 0.0

    if expected_type == "string":
        return 1.0  # Any column can be represented as string

    if expected_type == "boolean":
        return 1.0 if inferred_type in ("numeric", "string") else 0.5

    return 0.5


def _check_value_pattern_match(profile: Dict[str, Any], canonical_name: str) -> float:
    """
    CRITICAL RULE: Check value pattern semantic compatibility.
    Example: Column named 'value' with samples ['UPI', 'IMPS'] is NOT amount (return 0.0),
    but column 'value' with samples ['1000', '25000'] IS amount (return 1.0).
    """
    samples = profile.get("sample_values", [])
    inferred_type = profile.get("inferred_type", "string")
    num_pct = profile.get("numeric_compatibility_pct", 0.0)
    dt_pct = profile.get("datetime_compatibility_pct", 0.0)
    is_step = profile.get("is_integer_step", False)

    if canonical_name == "amount":
        # Amount MUST be numeric
        if num_pct >= 80.0 and not is_step:
            return 1.0
        return 0.0

    if canonical_name == "timestamp":
        if is_step or dt_pct >= 80.0:
            return 1.0
        return 0.0

    if canonical_name == "transaction_type":
        # Categorical strings (TRANSFER, CASH_OUT, PAYMENT, UPI, NEFT)
        if inferred_type == "string" and num_pct < 50.0 and dt_pct < 50.0:
            return 1.0
        return 0.5

    if canonical_name in ("sender_account_id", "receiver_account_id", "transaction_id"):
        # Account / Txn IDs can be alphanumeric strings or large integer IDs
        if inferred_type in ("string", "numeric", "integer_step"):
            return 1.0
        return 0.5

    if canonical_name == "is_mule_pattern":
        # Labels are 0/1 or True/False
        if samples and set(str(s).strip().lower() for s in samples).issubset({"0", "1", "true", "false", "0.0", "1.0"}):
            return 1.0
        return 0.5

    return 0.8


def evaluate_column_candidate(profile: Dict[str, Any], canonical_name: str) -> Dict[str, Any]:
    """
    Evaluate candidate score between a source column profile and a target canonical field.
    Uses 40/25/20/15 weighted scoring formula.
    """
    source_norm = profile.get("normalized_name", "")
    canonical_field = CANONICAL_FIELDS[canonical_name]

    # 1. Header similarity (40%)
    sim_score = _calculate_header_similarity(source_norm, canonical_name)

    # 2. Alias match (25%)
    alias_matched, alias_score = _check_alias_match(source_norm, canonical_field)

    # 3. Data type compatibility (20%)
    type_score = _check_type_compatibility(profile.get("inferred_type", "string"), canonical_field.expected_type)

    # 4. Value pattern match (15%)
    val_score = _check_value_pattern_match(profile, canonical_name)

    # Weighted final confidence score
    raw_confidence = (0.40 * max(sim_score, alias_score)) + (0.25 * alias_score) + (0.20 * type_score) + (0.15 * val_score)

    # Boost transaction_type for non-numeric string columns
    if canonical_name == "transaction_type" and val_score == 1.0 and type_score == 1.0:
        raw_confidence = max(0.85, raw_confidence)

    # Boost to 1.0 for exact alias or exact header match if type is compatible
    if (source_norm == canonical_name or source_norm in canonical_field.aliases) and val_score > 0.5:
        final_confidence = 0.99
    elif alias_matched and val_score > 0.5:
        final_confidence = max(0.92, round(raw_confidence, 2))
    else:
        final_confidence = round(min(1.0, raw_confidence), 2)

    return {
        "target": canonical_name,
        "confidence": final_confidence,
        "header_similarity": sim_score,
        "alias_score": alias_score,
        "type_score": type_score,
        "value_score": val_score,
    }


def map_columns(col_profiles: List[Dict[str, Any]]) -> ColumnMappingResult:
    """
    Multi-stage mapping engine with candidate scoring, collision resolution, and capability checks.
    """
    mappings: List[SingleColumnMapping] = []
    mapped_dict: Dict[str, str] = {}
    assigned_targets: Set[str] = set()

    # Step 1: Score all (source, canonical_target) pairs
    col_candidates: List[Tuple[Dict[str, Any], List[Dict[str, Any]]]] = []

    for profile in col_profiles:
        source_col = profile["source_column"]
        candidates = []
        for cname in CANONICAL_FIELDS:
            cand_eval = evaluate_column_candidate(profile, cname)
            if cand_eval["confidence"] > 0.25:
                candidates.append(cand_eval)
        candidates.sort(key=lambda x: x["confidence"], reverse=True)
        col_candidates.append((profile, candidates))

    # Step 2: Sort column candidates by highest top-confidence to resolve collisions greedily
    col_candidates.sort(key=lambda item: item[1][0]["confidence"] if item[1] else 0.0, reverse=True)

    for profile, candidates in col_candidates:
        source_col = profile["source_column"]
        chosen_target = None
        chosen_conf = 0.0
        matched_stage = "unmapped"

        for cand in candidates:
            tgt = cand["target"]
            conf = cand["confidence"]

            if tgt not in assigned_targets:
                chosen_target = tgt
                chosen_conf = conf
                assigned_targets.add(tgt)
                if conf >= 0.95:
                    matched_stage = "Stage 1 (Exact/Alias Match)"
                elif conf >= 0.85:
                    matched_stage = "Stage 2 (Alias & Type Match)"
                elif conf >= 0.70:
                    matched_stage = "Stage 3 (Fuzzy & Semantic Match)"
                else:
                    matched_stage = "Stage 4 (Low Confidence Candidate)"
                break

        if chosen_target and chosen_conf >= 0.70:
            if chosen_conf >= 0.90:
                status = "auto"
            else:
                status = "review"
            mapped_dict[source_col] = chosen_target
        else:
            status = "manual" if chosen_target else "unmapped"

        mappings.append(
            SingleColumnMapping(
                source=source_col,
                target=chosen_target,
                confidence=chosen_conf,
                status=status,
                matched_stage=matched_stage,
                inferred_type=profile.get("inferred_type", "string"),
                sample_values=profile.get("sample_values", []),
                candidate_targets=candidates[:3],
            )
        )

    # Preserve original header ordering in returned mappings list
    raw_header_order = [p["source_column"] for p in col_profiles]
    mappings.sort(key=lambda m: raw_header_order.index(m.source))

    # Step 3: Check missing mandatory source fields
    mapped_target_names = set(mapped_dict.values())
    missing_req = [
        fname for fname in MANDATORY_SOURCE_FIELDS if fname not in mapped_target_names
    ]

    unmapped = [m.source for m in mappings if m.status in ("manual", "unmapped")]

    # Capability flags
    can_predict = len(missing_req) == 0
    can_train = can_predict and ("is_mule_pattern" in mapped_target_names)

    if not can_predict:
        overall_status = "dataset_not_applicable"
    elif all(m.status == "auto" for m in mappings if m.target in MANDATORY_SOURCE_FIELDS):
        overall_status = "auto_ready"
    else:
        overall_status = "mapping_required"

    return ColumnMappingResult(
        status=overall_status,
        mappings=mappings,
        mapped_dict=mapped_dict,
        missing_required=missing_req,
        unmapped_columns=unmapped,
        can_train=can_train,
        can_predict=can_predict,
    )
