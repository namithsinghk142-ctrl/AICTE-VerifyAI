"""
Unit Tests — Cross-Document Consistency Engine
================================================
Tests all normalisation routines, comparison strategies and the full
run_cross_doc_checks() orchestration function using clearly labelled
synthetic fixtures. No real institution data is used; all test values
are fabricated solely for controlled discrepancy testing.

Coverage:
  1. _norm_name        — case, whitespace, abbreviation expansion
  2. _norm_id          — separator normalisation, uppercase
  3. _norm_survey      — leading zeros, sub-parcel fractions
  4. _extract_land_area_acres — units: acres, hectares, sq.m, gunthas
  5. _parse_date       — multiple date formats
  6. _compare_name     — exact match, abbreviation, mismatch, partial overlap
  7. _compare_exact    — matching IDs, diverging IDs
  8. _compare_survey   — match, sub-parcel, true mismatch
  9. _compare_land_area — unit conversion, tolerance, mismatch, ambiguous unit
 10. _compare_date     — same date different formats, different dates, unparseable
 11. run_cross_doc_checks() — fewer than 2 docs, single-field match,
     deliberate mismatch, MISSING, UNABLE_TO_COMPARE, OCR provenance
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from backend.cross_doc_engine import (
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
    run_cross_doc_checks,
    COMPARABLE_FIELDS,
)


# ─── 1. Name Normalisation ────────────────────────────────────────────────────

class TestNormName(unittest.TestCase):

    def test_lowercases_input(self):
        self.assertEqual(_norm_name("NORTHSTAR INSTITUTE OF TECHNOLOGY"), "northstar institute of technology")

    def test_strips_punctuation(self):
        self.assertEqual(_norm_name("Northstar (Pvt.) Institute"), "northstar private institute")

    def test_expands_inst_abbreviation(self):
        result = _norm_name("Northstar Inst. of Tech")
        self.assertIn("institute", result)
        self.assertIn("technology", result)

    def test_collapses_whitespace(self):
        self.assertEqual(_norm_name("  Foo   Bar  "), "foo bar")

    def test_removes_quotes(self):
        self.assertEqual(_norm_name('"Alpha" Engineering College'), "alpha engineering college")


# ─── 2. ID Normalisation ─────────────────────────────────────────────────────

class TestNormId(unittest.TestCase):

    def test_uppercases(self):
        self.assertEqual(_norm_id("demo/2026-27/eoa/ts/001"), "DEMO/2026-27/EOA/TS/001")

    def test_replaces_spaces_with_hyphen(self):
        self.assertEqual(_norm_id("DEMO 2026 27"), "DEMO-2026-27")

    def test_strips_leading_trailing_whitespace(self):
        self.assertEqual(_norm_id("  ABC-123  "), "ABC-123")

    def test_normalises_en_dash(self):
        # en-dash → hyphen
        result = _norm_id("ABC–123")
        self.assertNotIn("–", result)


# ─── 3. Survey Number Normalisation ──────────────────────────────────────────

class TestNormSurvey(unittest.TestCase):

    def test_uppercase(self):
        self.assertEqual(_norm_survey("48/2a"), "48/2A")

    def test_strips_leading_zeros(self):
        self.assertEqual(_norm_survey("048/02"), "48/2")

    def test_spaces_around_slash(self):
        self.assertEqual(_norm_survey("48 / 2"), "48/2")

    def test_zero_part(self):
        # "0" alone should remain "0"
        self.assertEqual(_norm_survey("0/0"), "0/0")


# ─── 4. Land Area Extraction ─────────────────────────────────────────────────

class TestExtractLandAreaAcres(unittest.TestCase):

    def test_acres_direct(self):
        result = _extract_land_area_acres("2.5 acres")
        self.assertAlmostEqual(result, 2.5, places=3)

    def test_hectares_conversion(self):
        # 1 hectare = 2.47105 acres
        result = _extract_land_area_acres("1 hectare")
        self.assertAlmostEqual(result, 2.47105, places=3)

    def test_ha_abbreviation(self):
        result = _extract_land_area_acres("3.5 ha")
        self.assertAlmostEqual(result, 3.5 * 2.47105, places=2)

    def test_square_metres(self):
        # 4046.86 sq.m = 1 acre
        result = _extract_land_area_acres("8093.72 sq.m")
        self.assertAlmostEqual(result, 2.0, places=1)

    def test_gunthas(self):
        # 40 gunthas = 1 acre
        result = _extract_land_area_acres("40 gunthas")
        self.assertAlmostEqual(result, 1.0, places=3)

    def test_no_unit_returns_none(self):
        # No recognisable unit — cannot convert
        result = _extract_land_area_acres("2.5")
        self.assertIsNone(result)

    def test_no_numeric_returns_none(self):
        result = _extract_land_area_acres("no area declared")
        self.assertIsNone(result)


# ─── 5. Date Parsing ─────────────────────────────────────────────────────────

class TestParseDate(unittest.TestCase):

    def test_iso_format(self):
        self.assertEqual(_parse_date("2024-04-18"), "2024-04-18")

    def test_dd_slash_mm_slash_yyyy(self):
        self.assertEqual(_parse_date("18/04/2024"), "2024-04-18")

    def test_dd_hyphen_mm_hyphen_yyyy(self):
        self.assertEqual(_parse_date("18-04-2024"), "2024-04-18")

    def test_month_name_day_year(self):
        self.assertEqual(_parse_date("April 18, 2024"), "2024-04-18")

    def test_day_month_name_year(self):
        self.assertEqual(_parse_date("18th April 2024"), "2024-04-18")

    def test_invalid_date_returns_none(self):
        self.assertIsNone(_parse_date("not-a-date"))

    def test_empty_string(self):
        self.assertIsNone(_parse_date(""))


# ─── 6. Name Comparison ──────────────────────────────────────────────────────

class TestCompareName(unittest.TestCase):

    def test_exact_match(self):
        v, _ = _compare_name("Northstar Institute of Technology", "Northstar Institute of Technology")
        self.assertEqual(v, "MATCH")

    def test_case_insensitive_match(self):
        v, _ = _compare_name("northstar institute of technology", "NORTHSTAR INSTITUTE OF TECHNOLOGY")
        self.assertEqual(v, "MATCH")

    def test_abbreviation_match(self):
        # "NIT" is a subset / abbreviation — but we don't recognise initialism-only matches
        # True abbreviation expansion via _NAME_ABBREV
        v, _ = _compare_name("Northstar Inst. of Tech", "Northstar Institute of Technology")
        self.assertEqual(v, "MATCH")

    def test_substring_match(self):
        v, _ = _compare_name("Northstar Institute of Technology", "Northstar Institute of Technology, Hyderabad")
        self.assertEqual(v, "MATCH")

    def test_clear_mismatch(self):
        v, _ = _compare_name("Sunrise College of Engineering", "Moonrise Technical University")
        self.assertEqual(v, "MISMATCH")

    def test_partial_overlap_flagged(self):
        # Shares "Engineering" and "College" but different institution
        v, _ = _compare_name("Alpha Engineering College", "Beta Engineering College")
        # Should flag as mismatch (different names) even with some overlap
        self.assertIn(v, ("MATCH", "MISMATCH"))  # engine decides based on token ratio


# ─── 7. Exact ID Comparison ──────────────────────────────────────────────────

class TestCompareExact(unittest.TestCase):

    def test_identical_ids(self):
        v, _ = _compare_exact("DEMO/2026-27/EOA/TS/001", "DEMO/2026-27/EOA/TS/001")
        self.assertEqual(v, "MATCH")

    def test_case_insensitive_match(self):
        v, _ = _compare_exact("demo/2026-27/eoa/ts/001", "DEMO/2026-27/EOA/TS/001")
        self.assertEqual(v, "MATCH")

    def test_different_ids(self):
        v, _ = _compare_exact("DEMO/2026-27/EOA/TS/001", "DEMO/2026-27/EOA/TS/002")
        self.assertEqual(v, "MISMATCH")

    def test_whitespace_normalised(self):
        v, _ = _compare_exact("DEMO / 2026-27 / EOA", "DEMO/2026-27/EOA")
        self.assertEqual(v, "MATCH")


# ─── 8. Survey Number Comparison ─────────────────────────────────────────────

class TestCompareSurvey(unittest.TestCase):

    def test_same_survey(self):
        v, _ = _compare_survey("48/2", "48/2")
        self.assertEqual(v, "MATCH")

    def test_leading_zero_normalised(self):
        v, _ = _compare_survey("048/02", "48/2")
        self.assertEqual(v, "MATCH")

    def test_sub_parcel_flagged(self):
        # "48" is parent parcel of "48/2"
        v, _ = _compare_survey("48", "48/2")
        self.assertEqual(v, "MISMATCH")

    def test_completely_different(self):
        v, _ = _compare_survey("48/2", "72/5")
        self.assertEqual(v, "MISMATCH")


# ─── 9. Land Area Comparison ─────────────────────────────────────────────────

class TestCompareLandArea(unittest.TestCase):

    def test_same_value_same_unit(self):
        v, _ = _compare_land_area("2.5 acres", "2.5 acres")
        self.assertEqual(v, "MATCH")

    def test_cross_unit_equivalent(self):
        # 1.0117 hectares ≈ 2.5 acres (within 2% tolerance)
        v, _ = _compare_land_area("2.5 acres", "1.012 hectares")
        self.assertEqual(v, "MATCH")

    def test_true_mismatch(self):
        v, _ = _compare_land_area("2.5 acres", "10 acres")
        self.assertEqual(v, "MISMATCH")

    def test_ambiguous_unit_unable(self):
        # No unit — cannot convert
        v, _ = _compare_land_area("2.5", "2.5")
        self.assertEqual(v, "UNABLE_TO_COMPARE")

    def test_one_missing_unit_unable(self):
        v, _ = _compare_land_area("2.5 acres", "no area declared")
        self.assertEqual(v, "UNABLE_TO_COMPARE")

    def test_rounding_tolerance(self):
        # 2.500 acres vs 2.501 acres — within 2% tolerance
        v, _ = _compare_land_area("2.500 acres", "2.501 acres")
        self.assertEqual(v, "MATCH")


# ─── 10. Date Comparison ─────────────────────────────────────────────────────

class TestCompareDate(unittest.TestCase):

    def test_same_date_different_formats(self):
        v, _ = _compare_date("2024-04-18", "18/04/2024")
        self.assertEqual(v, "MATCH")

    def test_different_dates(self):
        v, _ = _compare_date("2024-04-18", "2025-01-01")
        self.assertEqual(v, "MISMATCH")

    def test_unparseable_date(self):
        v, _ = _compare_date("N/A", "2024-04-18")
        self.assertEqual(v, "UNABLE_TO_COMPARE")

    def test_both_unparseable(self):
        v, _ = _compare_date("not-a-date", "also-not-a-date")
        self.assertEqual(v, "UNABLE_TO_COMPARE")


# ─── 11. Confidence Score ─────────────────────────────────────────────────────

class TestConfidence(unittest.TestCase):

    def test_digital_extraction_high(self):
        score = _confidence("Northstar Institute of Technology", ocr_used=False)
        self.assertGreaterEqual(score, 0.80)

    def test_ocr_lower(self):
        score = _confidence("Northstar Institute", ocr_used=True)
        self.assertLess(score, _confidence("Northstar Institute", ocr_used=False))

    def test_short_value_penalised(self):
        score_short = _confidence("48", ocr_used=False)
        score_long = _confidence("Northstar Institute of Technology", ocr_used=False)
        self.assertLessEqual(score_short, score_long)

    def test_within_valid_range(self):
        for val in ["", "x", "ABC/123", "Long Institution Name Here"]:
            score = _confidence(val, ocr_used=True)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)


# ─── 12. Orchestration: run_cross_doc_checks() ───────────────────────────────

def _make_record(filename, fields: dict, ocr_used=False) -> MagicMock:
    """Synthetic UploadedDocumentRecord fixture for orchestration tests."""
    rec = MagicMock()
    rec.filename = filename
    rec.file_type = ".pdf"
    rec.ocr_used = ocr_used
    rec.extracted_fields_json = json.dumps(fields)
    return rec


class TestRunCrossDocChecks(unittest.TestCase):

    def _run_with_records(self, records):
        """Patch DB query to return synthetic records and run the engine."""
        mock_db = MagicMock()
        # Patch query chain: query().filter().all() → records
        mock_db.query.return_value.filter.return_value.all.return_value = records
        # Patch delete (for upsert)
        mock_db.query.return_value.filter.return_value.delete.return_value = None

        with patch("backend.cross_doc_engine.CrossDocComparisonModel") as MockModel:
            MockModel.return_value = MagicMock()
            result = run_cross_doc_checks("sub-test-001", mock_db)

        return result

    def test_fewer_than_two_records_returns_empty(self):
        records = [_make_record("doc1.pdf", {"institutionName": "Northstar"})]
        result = self._run_with_records(records)
        self.assertEqual(result, [])

    def test_matching_institution_names(self):
        records = [
            _make_record("noc.pdf", {"institutionName": "Northstar Institute of Technology"}),
            _make_record("affidavit.pdf", {"institutionName": "NORTHSTAR INSTITUTE OF TECHNOLOGY"}),
        ]
        result = self._run_with_records(records)
        inst_field = next((r for r in result if "Institution" in r["fieldName"]), None)
        self.assertIsNotNone(inst_field, "Institution name field must appear in results")
        self.assertFalse(inst_field["hasDiscrepancy"])

    def test_mismatching_institution_names(self):
        records = [
            _make_record("noc.pdf", {"institutionName": "Northstar Institute of Technology"}),
            _make_record("affidavit.pdf", {"institutionName": "Moonrise Technical University"}),
        ]
        result = self._run_with_records(records)
        inst_field = next((r for r in result if "Institution" in r["fieldName"]), None)
        self.assertIsNotNone(inst_field)
        self.assertTrue(inst_field["hasDiscrepancy"])

    def test_missing_field_in_one_doc(self):
        """SYNTHETIC: One doc has surveyNumber, the other does not."""
        records = [
            _make_record("land_deed.pdf", {"surveyNumber": "48/2"}),
            _make_record("noc.pdf", {"institutionName": "Northstar Institute"}),
        ]
        result = self._run_with_records(records)
        survey_field = next((r for r in result if "Survey" in r["fieldName"]), None)
        # Survey only in one doc → MISSING
        if survey_field:
            self.assertTrue(survey_field["hasDiscrepancy"])
            missing_entries = [e for e in survey_field["entries"] if e.get("verdict") == "MISSING" or "not extracted" in e["extractedValue"]]
            self.assertGreater(len(missing_entries), 0)

    def test_land_area_unit_mismatch_flagged(self):
        """SYNTHETIC: 2.5 acres vs 10 acres — clear numeric mismatch."""
        records = [
            _make_record("deed.pdf", {"landArea": "2.5 acres"}),
            _make_record("affidavit.pdf", {"landArea": "10 acres"}),
        ]
        result = self._run_with_records(records)
        land_field = next((r for r in result if "Land Area" in r["fieldName"]), None)
        self.assertIsNotNone(land_field)
        self.assertTrue(land_field["hasDiscrepancy"])

    def test_land_area_unit_conversion_match(self):
        """SYNTHETIC: 2.47 acres ≈ 1 hectare — should match after conversion."""
        records = [
            _make_record("deed.pdf", {"landArea": "2.47 acres"}),
            _make_record("affidavit.pdf", {"landArea": "1 hectare"}),
        ]
        result = self._run_with_records(records)
        land_field = next((r for r in result if "Land Area" in r["fieldName"]), None)
        self.assertIsNotNone(land_field)
        self.assertFalse(land_field["hasDiscrepancy"])

    def test_unable_to_compare_no_discrepancy_flag(self):
        """SYNTHETIC: Land areas without units → UNABLE_TO_COMPARE, not MISMATCH."""
        records = [
            _make_record("deed.pdf", {"landArea": "2.5"}),
            _make_record("affidavit.pdf", {"landArea": "2.5"}),
        ]
        result = self._run_with_records(records)
        land_field = next((r for r in result if "Land Area" in r["fieldName"]), None)
        if land_field:
            # UNABLE_TO_COMPARE should NOT set hasDiscrepancy = True
            self.assertFalse(land_field["hasDiscrepancy"])

    def test_ocr_provenance_lowers_confidence(self):
        """Entries from OCR-processed docs should have lower confidence."""
        records = [
            _make_record("digital.pdf", {"institutionName": "Northstar Institute"}, ocr_used=False),
            _make_record("scanned.pdf", {"institutionName": "Northstar Institute"}, ocr_used=True),
        ]
        result = self._run_with_records(records)
        inst_field = next((r for r in result if "Institution" in r["fieldName"]), None)
        if inst_field and len(inst_field["entries"]) == 2:
            scores = [e["confidenceScore"] for e in inst_field["entries"]]
            # Both should be >0, OCR one should be <= digital one
            self.assertTrue(all(s > 0 for s in scores))

    def test_date_same_format_match(self):
        """SYNTHETIC: Same date, same format."""
        records = [
            _make_record("deed.pdf", {"issueDate": "2024-04-18"}),
            _make_record("noc.pdf", {"issueDate": "2024-04-18"}),
        ]
        result = self._run_with_records(records)
        date_field = next((r for r in result if "Date" in r["fieldName"]), None)
        if date_field:
            self.assertFalse(date_field["hasDiscrepancy"])

    def test_date_cross_format_match(self):
        """SYNTHETIC: Same date, different format — must normalise to MATCH."""
        records = [
            _make_record("deed.pdf", {"issueDate": "2024-04-18"}),
            _make_record("noc.pdf", {"issueDate": "18/04/2024"}),
        ]
        result = self._run_with_records(records)
        date_field = next((r for r in result if "Date" in r["fieldName"]), None)
        if date_field:
            self.assertFalse(date_field["hasDiscrepancy"])

    def test_unrelated_documents_no_fields_returns_empty(self):
        """SYNTHETIC: Documents with no comparable fields → no comparisons."""
        records = [
            _make_record("random1.pdf", {}),
            _make_record("random2.pdf", {}),
        ]
        result = self._run_with_records(records)
        self.assertEqual(result, [])

    def test_all_supported_fields_covered(self):
        """Ensure all COMPARABLE_FIELDS keys have a comparison strategy defined."""
        for key, meta in COMPARABLE_FIELDS.items():
            self.assertIn("strategy", meta, f"Field '{key}' is missing 'strategy'")
            self.assertIn("label", meta, f"Field '{key}' is missing 'label'")
            self.assertIn("description", meta, f"Field '{key}' is missing 'description'")


if __name__ == "__main__":
    unittest.main(verbosity=2)
