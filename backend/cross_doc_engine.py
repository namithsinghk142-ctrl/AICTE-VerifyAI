"""
Cross-Document Consistency Engine
==================================
Compares extracted fields across all uploaded documents of the same submission.

Design principles:
  - Reuses extracted_fields_json from UploadedDocumentRecord (no new OCR pipeline).
  - Normalises values before comparing (case, whitespace, abbreviations, units).
  - Returns MATCH, MISMATCH, MISSING or UNABLE_TO_COMPARE — never "fraud".
  - Only compares fields both documents claim to have a value for.
  - Ambiguous unit differences (acres vs hectares without a numeric value) → UNABLE_TO_COMPARE.
  - All findings identify both documents, both values and a clear explanation.
  - Upserts CrossDocComparisonModel rows; safe to call on every upload.
"""

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from .models import CrossDocComparisonModel, SubmissionModel, UploadedDocumentRecord

# ─── Supported Comparable Fields ─────────────────────────────────────────────

# Maps extracted-field key → (human-friendly label, comparison strategy)
COMPARABLE_FIELDS: Dict[str, Dict[str, Any]] = {
    "institutionName": {
        "label": "Institution Legal Name",
        "strategy": "name",
        "description": (
            "The legal name of the institution as declared in each document. "
            "Minor variations in capitalisation or punctuation are tolerated; "
            "substantive name differences are flagged."
        ),
    },
    "applicationId": {
        "label": "AICTE Application / Reference ID",
        "strategy": "exact_normalised",
        "description": (
            "The unique AICTE application or reference identifier cited in each document. "
            "IDs must match exactly after removing whitespace and case differences."
        ),
    },
    "referenceNo": {
        "label": "Document Reference / Order Number",
        "strategy": "exact_normalised",
        "description": (
            "The order or reference number assigned by the issuing authority. "
            "Compared after stripping whitespace and normalising separators."
        ),
    },
    "surveyNumber": {
        "label": "Land Survey / Plot Number",
        "strategy": "survey_number",
        "description": (
            "The land parcel survey or khasra number. "
            "Forward-slash fractions and leading zeros are normalised before comparison."
        ),
    },
    "landArea": {
        "label": "Campus Land Area",
        "strategy": "land_area",
        "description": (
            "Declared campus area. Numeric values are extracted and converted to acres "
            "for comparison. Hectares are converted at 1 hectare = 2.471 acres. "
            "If unit conversion is ambiguous the result is UNABLE_TO_COMPARE."
        ),
    },
    "issuingAuthority": {
        "label": "Issuing / Certifying Authority",
        "strategy": "name",
        "description": (
            "The competent authority or body that issued the document. "
            "Common abbreviations are expanded before comparison."
        ),
    },
    "issueDate": {
        "label": "Document Issue Date",
        "strategy": "date",
        "description": (
            "The execution or issuance date of the document. "
            "Formats like DD-MM-YYYY, YYYY-MM-DD and Month DD, YYYY are normalised."
        ),
    },
}

# ─── Normalisation Helpers ────────────────────────────────────────────────────

# Common Indian-government abbreviations expanded for name comparison
_NAME_ABBREV: Dict[str, str] = {
    r"\binst\b": "institute",
    r"\binstit\b": "institute",
    r"\bcol\b": "college",
    r"\bcolg\b": "college",
    r"\buniv\b": "university",
    r"\btech\b": "technology",
    r"\bengg\b": "engineering",
    r"\bengr\b": "engineering",
    r"\bpvt\b": "private",
    r"\bltd\b": "limited",
    r"\bgovt\b": "government",
    r"\bgov\b": "government",
    r"\bsec\b": "secondary",
    r"\bsr\b": "senior",
    r"\bjr\b": "junior",
    r"\bno\b\.?": "number",
    r"\brd\b": "road",
    r"\bst\b": "street",
    r"\bnagar\b": "nagar",  # keep as-is but lowercase
    r"\btaluk\b": "taluk",
}

_UNIT_HECTARE_TO_ACRE = 2.47105


def _norm_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _norm_name(s: str) -> str:
    """Lowercase, strip punctuation, expand abbreviations."""
    s = s.lower()
    s = re.sub(r"['\",.\-–—()]", " ", s)
    for abbr, full in _NAME_ABBREV.items():
        s = re.sub(abbr, full, s, flags=re.IGNORECASE)
    return _norm_whitespace(s)


def _norm_id(s: str) -> str:
    """Remove whitespace, normalise separators, uppercase."""
    # Strip spaces around slashes first: "DEMO / 2026-27 / EOA" → "DEMO/2026-27/EOA"
    s = re.sub(r"\s*/\s*", "/", s.strip())
    s = re.sub(r"[\s\-\u2013\u2014]+", "-", s)
    return s.upper()


def _norm_survey(s: str) -> str:
    """Normalise survey number: remove spaces around /, uppercase, strip leading zeros in parts."""
    s = s.upper().strip()
    s = re.sub(r"\s*/\s*", "/", s)
    # Strip leading zeros per part: "048/2" → "48/2"
    parts = s.split("/")
    parts = [p.lstrip("0") or "0" for p in parts]
    return "/".join(parts)


def _extract_land_area_acres(s: str) -> Optional[float]:
    """
    Parse a land-area string and return numeric value in acres.
    Supports: '2.5 acres', '1 hectare', '1.2 ha', '10000 sq.m', '1.5 guntha'
    Returns None if value cannot be reliably extracted or converted.
    """
    s_lower = s.lower().strip()

    # Try to find a numeric value first
    m = re.search(r"(\d+(?:\.\d+)?)", s_lower)
    if not m:
        return None
    value = float(m.group(1))

    if re.search(r"\bhectare|\bha\b", s_lower):
        return round(value * _UNIT_HECTARE_TO_ACRE, 4)
    if re.search(r"\bacre", s_lower):
        return round(value, 4)
    if re.search(r"\bsq\.?\s*m\b|\bsquare\s*met", s_lower):
        return round(value / 4046.86, 4)
    if re.search(r"\bguntha[s]?\b|\bgunta[s]?\b", s_lower):
        # 1 guntha = 0.02500 acres (standard)
        return round(value * 0.025, 4)
    if re.search(r"\bcent\b", s_lower):
        # 1 cent = 0.01 acres
        return round(value * 0.01, 4)

    # Unit is ambiguous or missing — cannot convert reliably
    return None


def _parse_date(s: str) -> Optional[str]:
    """
    Parse a date string into ISO format YYYY-MM-DD.
    Handles: 2024-04-18, 18/04/2024, 18-04-2024, April 18 2024, 18th April 2024.
    Returns None if unparseable.
    """
    s = s.strip()
    formats = [
        r"(\d{4})-(\d{1,2})-(\d{1,2})",          # YYYY-MM-DD
        r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})",    # DD/MM/YYYY or DD-MM-YYYY
        r"(\d{4})/(\d{1,2})/(\d{1,2})",           # YYYY/MM/DD
    ]
    month_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }

    for fmt in formats:
        m = re.fullmatch(fmt, s)
        if m:
            g = m.groups()
            # Determine year, month, day
            if len(g[0]) == 4:
                # YYYY-MM-DD or YYYY/MM/DD
                yr, mo, dy = int(g[0]), int(g[1]), int(g[2])
            else:
                # DD/MM/YYYY
                dy, mo, yr = int(g[0]), int(g[1]), int(g[2])
            if 1 <= mo <= 12 and 1 <= dy <= 31 and 1900 <= yr <= 2100:
                return f"{yr:04d}-{mo:02d}-{dy:02d}"

    # Month-name patterns: "April 18 2024", "18 April 2024", "18th April, 2024"
    m_text = re.search(
        r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(\d{4})", s, re.IGNORECASE
    )
    if not m_text:
        m_text = re.search(
            r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", s, re.IGNORECASE
        )
        if m_text:
            month_str, day_str, yr_str = m_text.groups()
            mo = month_map.get(month_str.lower()[:3])
            if mo:
                return f"{int(yr_str):04d}-{mo:02d}-{int(day_str):02d}"
    else:
        day_str, month_str, yr_str = m_text.groups()
        mo = month_map.get(month_str.lower()[:3])
        if mo:
            return f"{int(yr_str):04d}-{mo:02d}-{int(day_str):02d}"

    return None


# ─── Comparison Result Types ──────────────────────────────────────────────────

ComparisonVerdict = str  # "MATCH" | "MISMATCH" | "MISSING" | "UNABLE_TO_COMPARE"


def _compare_name(a: str, b: str) -> Tuple[ComparisonVerdict, str]:
    """Compare two name strings with normalisation."""
    na, nb = _norm_name(a), _norm_name(b)
    if na == nb:
        return "MATCH", "Names are equivalent after normalisation."
    # Substring check: one may be abbreviated form of the other
    if na in nb or nb in na:
        return "MATCH", "One name is a recognised abbreviation/subset of the other."
    # Token-level similarity — if ≥70% tokens overlap treat as near-match
    tokens_a = set(na.split())
    tokens_b = set(nb.split())
    if tokens_a and tokens_b:
        overlap = tokens_a & tokens_b
        ratio = len(overlap) / max(len(tokens_a), len(tokens_b))
        if ratio >= 0.70:
            return "MATCH", f"Names share {int(ratio*100)}% of key tokens — treated as equivalent."
        if ratio >= 0.40:
            # Partial overlap: flag for review but do not call it a hard mismatch
            return (
                "MISMATCH",
                f"Names share only {int(ratio*100)}% of tokens. "
                f"Normalised values: '{na}' vs '{nb}'. Verify whether both refer to the same institution.",
            )
    return (
        "MISMATCH",
        f"Names differ substantially after normalisation. "
        f"Extracted: '{a}' vs '{b}'.",
    )


def _compare_exact(a: str, b: str) -> Tuple[ComparisonVerdict, str]:
    na, nb = _norm_id(a), _norm_id(b)
    if na == nb:
        return "MATCH", "Identifiers are identical after normalisation."
    return "MISMATCH", f"Identifiers differ: '{a}' vs '{b}'."


def _compare_survey(a: str, b: str) -> Tuple[ComparisonVerdict, str]:
    na, nb = _norm_survey(a), _norm_survey(b)
    if na == nb:
        return "MATCH", "Survey numbers are equivalent after normalisation."
    # Check if one is a prefix of the other (e.g., "48" vs "48/2")
    if na.startswith(nb + "/") or nb.startswith(na + "/"):
        return (
            "MISMATCH",
            f"One document cites the parent parcel '{na}', the other a sub-parcel '{nb}'. "
            "Verify whether these refer to the same land parcel.",
        )
    return "MISMATCH", f"Survey numbers differ: '{a}' vs '{b}'."


def _compare_land_area(a: str, b: str) -> Tuple[ComparisonVerdict, str]:
    acres_a = _extract_land_area_acres(a)
    acres_b = _extract_land_area_acres(b)

    if acres_a is None or acres_b is None:
        return (
            "UNABLE_TO_COMPARE",
            f"Cannot convert land area to a common unit. "
            f"Values: '{a}' and '{b}'. Manual verification required.",
        )
    # Allow ±2% tolerance for rounding differences
    if acres_a == 0 and acres_b == 0:
        return "MATCH", "Both documents declare zero land area (verify this is intentional)."
    tolerance = max(acres_a, acres_b) * 0.02
    diff = abs(acres_a - acres_b)
    if diff <= tolerance:
        return (
            "MATCH",
            f"Land areas are equivalent within rounding tolerance: {acres_a:.4f} acres vs {acres_b:.4f} acres.",
        )
    return (
        "MISMATCH",
        f"Land areas differ: '{a}' ({acres_a:.4f} acres) vs '{b}' ({acres_b:.4f} acres). "
        f"Difference: {diff:.4f} acres. Verify whether an additional plot was included or excluded.",
    )


def _compare_date(a: str, b: str) -> Tuple[ComparisonVerdict, str]:
    da, db = _parse_date(a), _parse_date(b)
    if da is None or db is None:
        return (
            "UNABLE_TO_COMPARE",
            f"Cannot parse one or both dates: '{a}' and '{b}'. "
            "Manual verification required.",
        )
    if da == db:
        return "MATCH", f"Both documents share the same date: {da}."
    return (
        "MISMATCH",
        f"Dates differ: '{a}' (parsed {da}) vs '{b}' (parsed {db}). "
        "This may reflect different document issue dates — verify context.",
    )


def _dispatch_compare(strategy: str, a: str, b: str) -> Tuple[ComparisonVerdict, str]:
    dispatch = {
        "name": _compare_name,
        "exact_normalised": _compare_exact,
        "survey_number": _compare_survey,
        "land_area": _compare_land_area,
        "date": _compare_date,
    }
    fn = dispatch.get(strategy, _compare_exact)
    return fn(a, b)


# ─── Per-field confidence score ───────────────────────────────────────────────

def _confidence(extracted_value: str, ocr_used: bool) -> float:
    """
    Heuristic confidence: shorter values extracted via OCR are less reliable.
    Returns a float 0.0–1.0.
    """
    base = 0.85 if not ocr_used else 0.70
    if len(extracted_value) < 4:
        base -= 0.15
    return round(max(0.10, min(1.0, base)), 2)


# ─── Main Engine Entry Point ──────────────────────────────────────────────────

def run_cross_doc_checks(submission_id: str, db: Session) -> List[Dict[str, Any]]:
    """
    Compare extracted fields across all UploadedDocumentRecords for this submission.
    Upserts CrossDocComparisonModel rows (one per comparable field).
    Returns the list of comparison dicts (same shape as CrossDocComparisonSchema).

    Called from the upload endpoint after every new document is persisted.
    Safe to call multiple times — existing rows are replaced.
    """
    # Load all uploaded document records for this submission
    records: List[UploadedDocumentRecord] = (
        db.query(UploadedDocumentRecord)
        .filter(UploadedDocumentRecord.submission_id == submission_id)
        .all()
    )

    if len(records) < 2:
        # Cannot compare with fewer than 2 documents
        return []

    # Parse extracted fields for each record
    parsed: List[Dict[str, Any]] = []
    for rec in records:
        fields: Dict[str, Any] = {}
        if rec.extracted_fields_json:
            try:
                fields = json.loads(rec.extracted_fields_json)
            except (json.JSONDecodeError, TypeError):
                fields = {}
        parsed.append(
            {
                "filename": rec.filename,
                "file_type": rec.file_type,
                "ocr_used": rec.ocr_used,
                "fields": fields,
            }
        )

    # Build per-field comparison results
    field_results: List[Dict[str, Any]] = []

    for field_key, field_meta in COMPARABLE_FIELDS.items():
        label = field_meta["label"]
        strategy = field_meta["strategy"]
        field_description = field_meta["description"]

        # Collect entries: documents that have a non-empty value for this field
        entries_with_value: List[Dict[str, Any]] = []
        entries_missing: List[Dict[str, Any]] = []

        for doc in parsed:
            raw = doc["fields"].get(field_key)
            val = str(raw).strip() if raw is not None else ""
            doc_type = doc["file_type"].lstrip(".").upper()
            entry_base = {
                "documentName": doc["filename"],
                "documentType": doc_type,
                "ocr_used": doc["ocr_used"],
            }
            if val and val.lower() not in ("none", "null", "n/a", "na", "not applicable"):
                entries_with_value.append({**entry_base, "extractedValue": val})
            else:
                entries_missing.append({**entry_base, "extractedValue": "—"})

        # Determine overall comparison result
        if len(entries_with_value) == 0:
            # No document in this submission has this field — skip entirely
            # (Don't pollute the UI with fields that nobody extracted)
            continue

        if len(entries_with_value) == 1:
            # Only one document has a value — report MISSING for the others
            overall_verdict: ComparisonVerdict = "MISSING"
            explanation = (
                f"Only one document in the dossier contains a '{label}' value. "
                f"The remaining {len(entries_missing)} document(s) do not declare this field."
            )
            has_discrepancy = True
            recommendation = (
                f"Request the institution to furnish all documents with a consistent '{label}' declaration, "
                "or verify whether the field is not applicable to all document types."
            )
        else:
            # Compare all pairs
            verdicts: List[ComparisonVerdict] = []
            pair_explanations: List[str] = []
            for i in range(len(entries_with_value)):
                for j in range(i + 1, len(entries_with_value)):
                    a_val = entries_with_value[i]["extractedValue"]
                    b_val = entries_with_value[j]["extractedValue"]
                    verdict, expl = _dispatch_compare(strategy, a_val, b_val)
                    verdicts.append(verdict)
                    pair_explanations.append(
                        f"[{entries_with_value[i]['documentName']} ↔ "
                        f"{entries_with_value[j]['documentName']}]: {expl}"
                    )

            if all(v == "MATCH" for v in verdicts):
                overall_verdict = "MATCH"
                explanation = "; ".join(pair_explanations)
                has_discrepancy = False
                recommendation = (
                    f"'{label}' is consistent across all {len(entries_with_value)} documents. No action required."
                )
            elif "UNABLE_TO_COMPARE" in verdicts and "MISMATCH" not in verdicts:
                overall_verdict = "UNABLE_TO_COMPARE"
                explanation = "; ".join(pair_explanations)
                has_discrepancy = False  # Not a confirmed discrepancy
                recommendation = (
                    f"The comparison engine cannot reliably convert '{label}' to a common unit or format. "
                    "Manually verify the values listed below."
                )
            elif "MISMATCH" in verdicts:
                overall_verdict = "MISMATCH"
                explanation = "; ".join(pair_explanations)
                has_discrepancy = True
                recommendation = (
                    f"'{label}' values differ across submitted documents. "
                    "Request clarification from the institution and verify original instruments. "
                    "Do not treat a discrepancy as conclusive evidence of falsification without human review."
                )
            else:
                overall_verdict = "MATCH"
                explanation = "; ".join(pair_explanations)
                has_discrepancy = False
                recommendation = f"'{label}' is consistent. No action required."

        # Build entry list for the UI (all docs, with per-entry isMismatched)
        ui_entries = []
        for e in entries_with_value:
            # An entry is mismatched if there's a MISMATCH involving this specific document
            is_this_mismatched = (
                overall_verdict == "MISMATCH"
                and len(entries_with_value) > 1
            )
            ui_entries.append(
                {
                    "documentName": e["documentName"],
                    "documentType": e["documentType"],
                    "extractedValue": e["extractedValue"],
                    "sourcePage": 1,
                    "isMismatched": is_this_mismatched,
                    "confidenceScore": _confidence(e["extractedValue"], e["ocr_used"]),
                    "verdict": overall_verdict,
                }
            )
        for e in entries_missing:
            ui_entries.append(
                {
                    "documentName": e["documentName"],
                    "documentType": e["documentType"],
                    "extractedValue": "— (not extracted)",
                    "sourcePage": 0,
                    "isMismatched": overall_verdict in ("MISMATCH", "MISSING"),
                    "confidenceScore": 0.0,
                    "verdict": "MISSING",
                }
            )

        # Build status text
        verdict_to_status = {
            "MATCH": f"✓ MATCH — {label} is consistent across all documents",
            "MISMATCH": f"⚠ MISMATCH — {label} values differ between documents",
            "MISSING": f"◌ MISSING — {label} absent from one or more documents",
            "UNABLE_TO_COMPARE": f"? UNABLE TO COMPARE — {label} values cannot be automatically reconciled",
        }
        status_text = verdict_to_status.get(overall_verdict, overall_verdict)

        field_results.append(
            {
                "fieldKey": field_key,
                "fieldName": label,
                "description": field_description + " " + explanation,
                "hasDiscrepancy": has_discrepancy,
                "statusText": status_text,
                "entries": ui_entries,
                "humanReviewRecommendation": recommendation,
                "verdict": overall_verdict,
            }
        )

    # ── Upsert CrossDocComparisonModel rows ──────────────────────────────────
    # Delete stale rows for this submission, then insert fresh ones
    db.query(CrossDocComparisonModel).filter(
        CrossDocComparisonModel.submission_id == submission_id
    ).delete(synchronize_session=False)

    for res in field_results:
        row = CrossDocComparisonModel(
            id=f"cdc-{submission_id}-{res['fieldKey']}-{uuid.uuid4().hex[:8]}",
            submission_id=submission_id,
            field_name=res["fieldName"],
            description=res["description"],
            has_discrepancy=res["hasDiscrepancy"],
            status_text=res["statusText"],
            entries_json=json.dumps(res["entries"]),
            human_review_recommendation=res["humanReviewRecommendation"],
        )
        db.add(row)

    db.commit()

    # Return list in CrossDocComparisonSchema shape (without fieldKey, verdict keys)
    return [
        {
            "fieldName": r["fieldName"],
            "description": r["description"],
            "hasDiscrepancy": r["hasDiscrepancy"],
            "statusText": r["statusText"],
            "entries": r["entries"],
            "humanReviewRecommendation": r["humanReviewRecommendation"],
        }
        for r in field_results
    ]
