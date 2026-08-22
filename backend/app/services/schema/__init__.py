"""
app/services/schema
===================
Universal CSV Ingestion and Schema Normalization Layer for MuleDetector.
"""

from app.services.schema.canonical_schema import (
    CANONICAL_FIELDS,
    CanonicalField,
    REQUIRED_CANONICAL_FIELDS,
    OPTIONAL_CANONICAL_FIELDS,
    ALIAS_DICTIONARY,
)
from app.services.schema.profiler import profile_csv
from app.services.schema.column_mapper import map_columns, ColumnMappingResult
from app.services.schema.validator import validate_normalized_dataframe
from app.services.schema.normalizer import normalize_dataset, normalize_and_save_dataset

__all__ = [
    "CANONICAL_FIELDS",
    "CanonicalField",
    "REQUIRED_CANONICAL_FIELDS",
    "OPTIONAL_CANONICAL_FIELDS",
    "ALIAS_DICTIONARY",
    "profile_csv",
    "map_columns",
    "ColumnMappingResult",
    "validate_normalized_dataframe",
    "normalize_dataset",
    "normalize_and_save_dataset",
]
