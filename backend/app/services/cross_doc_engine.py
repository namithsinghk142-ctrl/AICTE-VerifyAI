"""Cross-Document Consistency Engine integration module for active VerifyAI app."""

from __future__ import annotations

import sys
import os

# Ensure backend root is on path for unified cross_doc_engine import
backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from cross_doc_engine import (
    COMPARABLE_FIELDS,
    FIELD_ALIASES,
    run_cross_doc_checks,
    _norm_name,
    _norm_id,
    _norm_survey,
    _extract_land_area_acres,
    _parse_date,
    _compare_name,
    _compare_exact,
    _compare_survey,
    _compare_land_area,
    _compare_date,
    _confidence,
)

__all__ = [
    "COMPARABLE_FIELDS",
    "FIELD_ALIASES",
    "run_cross_doc_checks",
    "_norm_name",
    "_norm_id",
    "_norm_survey",
    "_extract_land_area_acres",
    "_parse_date",
    "_compare_name",
    "_compare_exact",
    "_compare_survey",
    "_compare_land_area",
    "_compare_date",
    "_confidence",
]
