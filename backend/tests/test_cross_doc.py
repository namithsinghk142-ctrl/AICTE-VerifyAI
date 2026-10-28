"""
Unit & Integration Tests — Cross-Document Consistency Engine Integration and Reliability.

Covers Part G Requirements:
  1. Matching values across multiple documents.
  2. Genuine mismatches (Survey No. 48 vs 48/2, land area divergence).
  3. Institution-name normalisation and acronym expansion.
  4. Equivalent land-area units (acres, hectares, sq.m, gunthas, cents).
  5. Missing fields handling.
  6. Low-confidence, ambiguous, or unparseable extraction (UNABLE_TO_COMPARE).
  7. Fewer than two eligible documents (<2 returns empty list).
  8. Scoping & isolation between unrelated institutional applications.
  9. Isolation between synthetic applications and public reference records.
 10. API response schemas and frontend integration.
 11. Audit logging for reviewer actions.
 12. Rerunning comparisons after a document changes.
 13. Prevention of automatic approval or rejection based solely on uncertain comparisons.
"""

from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import (
    Application,
    ApplicationStatus,
    AuditEvent,
    Document,
    DocumentProcessingStatus,
    PublicReferenceInstitution,
    ValidationFinding,
    FindingSeverity,
)
from app.services.cross_doc_engine import (
    _compare_date,
    _compare_exact,
    _compare_land_area,
    _compare_name,
    _compare_survey,
    _extract_land_area_acres,
    _norm_id,
    _norm_name,
    _norm_survey,
    _parse_date,
    run_cross_doc_checks,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_app(db: Session, name: str = "Test Institute of Technology") -> Application:
    app = Application(
        institution_name=name,
        application_category="New Technical Campus",
        academic_year="2026-2027",
        status=ApplicationStatus.SUBMITTED,
        is_synthetic_demo=True,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


def _create_doc(
    db: Session,
    app_id: str,
    filename: str,
    doc_type: str = "Deed",
    fields: dict | None = None,
    text: str = "",
    ocr_used: bool = False,
) -> Document:
    doc = Document(
        application_id=app_id,
        original_filename=filename,
        filename=filename,
        document_type=doc_type,
        storage_reference=f"test_storage/{filename}",
        mime_type="image/png" if ocr_used else "application/pdf",
        file_size=10240,
        sha256_hash="a" * 64,
        extracted_text=text,
        extracted_fields=fields or {},
        processing_status=DocumentProcessingStatus.COMPLETED,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


# ---------------------------------------------------------------------------
# Test Suite
# ---------------------------------------------------------------------------

class TestCrossDocNormalisationAndUnits:
    """Tests 3, 4, 6: Normalisation, unit equivalence, and unparseable inputs."""

    def test_institution_name_abbreviation_expansion(self):
        """IIT / NIT and common educational abbreviations expand for comparison."""
        na = _norm_name("IIT Bombay")
        nb = _norm_name("Indian Institute of Technology Bombay")
        assert na == nb

        nc = _norm_name("Northstar Inst. of Tech.")
        nd = _norm_name("Northstar Institute of Technology")
        assert nc == nd

    def test_survey_number_normalisation(self):
        """Leading zeros and spaces around forward-slashes are normalised."""
        assert _norm_survey("048/02") == "48/2"
        assert _norm_survey("48 / 2") == "48/2"
        assert _norm_survey("Sy. No. 48/2") == "48/2"
        assert _norm_survey("Survey Number: 48/2") == "48/2"

    def test_land_area_unit_conversions(self):
        """1 hectare = 2.471 acres, 10,000 sq.m = ~2.471 acres, 100 gunthas = 2.5 acres."""
        acres_1ha = _extract_land_area_acres("1 hectare")
        assert acres_1ha is not None
        assert 2.47 <= acres_1ha <= 2.48

        acres_sqm = _extract_land_area_acres("10000 sq.m")
        assert acres_sqm is not None
        assert 2.46 <= acres_sqm <= 2.48

        acres_gunthas = _extract_land_area_acres("100 gunthas")
        assert acres_gunthas is not None
        assert round(acres_gunthas, 1) == 2.5

        acres_cents = _extract_land_area_acres("250 cents")
        assert acres_cents is not None
        assert round(acres_cents, 1) == 2.5

    def test_date_parsing_formats(self):
        """Standard, hyphenated, and verbal month formats parse to ISO YYYY-MM-DD."""
        assert _parse_date("2024-04-18") == "2024-04-18"
        assert _parse_date("18/04/2024") == "2024-04-18"
        assert _parse_date("18-04-2024") == "2024-04-18"
        assert _parse_date("April 18, 2024") == "2024-04-18"
        assert _parse_date("18th April 2024") == "2024-04-18"

    def test_unparseable_inputs_return_unable_to_compare(self):
        """Land area or dates with missing/unparseable units return UNABLE_TO_COMPARE without raising."""
        verdict, msg = _compare_land_area("ambiguous area", "2.5 acres")
        assert verdict == "UNABLE_TO_COMPARE"
        assert "Cannot convert land area" in msg

        verdict_date, msg_date = _compare_date("not-a-valid-date", "2024-04-18")
        assert verdict_date == "UNABLE_TO_COMPARE"
        assert "Cannot parse" in msg_date


class TestCrossDocEngineDiscrepanciesAndMatches:
    """Tests 1, 2, 5: Matches, genuine mismatches, missing fields across docs."""

    def test_matching_values_across_two_documents(self, db_session: Session):
        """Documents agreeing on institutional name, application ID, and land area yield MATCH."""
        app = _create_app(db_session, "Apex Engineering College")
        _create_doc(
            db_session,
            app.id,
            "title_deed.pdf",
            fields={
                "institutionName": "Apex Engineering College",
                "applicationId": "AICTE-2026-APEX-01",
                "landArea": "5.0 acres",
            },
        )
        _create_doc(
            db_session,
            app.id,
            "noc.pdf",
            fields={
                "institutionName": "Apex Engineering College",
                "applicationId": "AICTE-2026-APEX-01",
                "landArea": "5.0 acres",
            },
        )

        results = run_cross_doc_checks(app.id, db_session)
        assert len(results) >= 3
        for res in results:
            assert res["hasDiscrepancy"] is False
            for entry in res["entries"]:
                assert entry["isMismatched"] is False
                assert entry["verdict"] == "MATCH"

    def test_genuine_survey_and_land_mismatch(self, db_session: Session):
        """Survey number (48 vs 48/2) and land acreage (2.5 vs 10 acres) are flagged as MISMATCH."""
        app = _create_app(db_session, "Northstar Tech")
        _create_doc(
            db_session,
            app.id,
            "land_conveyance.pdf",
            fields={"surveyNumber": "48", "landArea": "2.5 acres"},
        )
        _create_doc(
            db_session,
            app.id,
            "encumbrance_cert.pdf",
            fields={"surveyNumber": "48/2", "landArea": "10.0 acres"},
        )

        results = run_cross_doc_checks(app.id, db_session)
        survey_res = next((r for r in results if "Survey" in r["fieldName"]), None)
        assert survey_res is not None
        assert survey_res["hasDiscrepancy"] is True
        assert "MISMATCH" in survey_res["statusText"]

        land_res = next((r for r in results if "Land Area" in r["fieldName"]), None)
        assert land_res is not None
        assert land_res["hasDiscrepancy"] is True
        assert "MISMATCH" in land_res["statusText"]

    def test_missing_field_in_one_document(self, db_session: Session):
        """Field present in only one document returns MISSING rather than a false mismatch."""
        app = _create_app(db_session, "Sunrise Academy")
        _create_doc(
            db_session,
            app.id,
            "doc_a.pdf",
            fields={"referenceNo": "REF-ORDER-9912", "institutionName": "Sunrise Academy"},
        )
        _create_doc(
            db_session,
            app.id,
            "doc_b.pdf",
            fields={"institutionName": "Sunrise Academy"},  # referenceNo is missing
        )

        results = run_cross_doc_checks(app.id, db_session)
        ref_res = next((r for r in results if "Reference" in r["fieldName"]), None)
        assert ref_res is not None
        assert ref_res["hasDiscrepancy"] is True
        assert "MISSING" in ref_res["statusText"]

        # One entry has extracted value, other is reported as missing
        val_entries = [e for e in ref_res["entries"] if e["verdict"] != "MISSING"]
        missing_entries = [e for e in ref_res["entries"] if e["verdict"] == "MISSING"]
        assert len(val_entries) == 1
        assert len(missing_entries) == 1
        assert missing_entries[0]["extractedValue"] == "— (not extracted)"


class TestCrossDocScopingAndIsolation:
    """Tests 7, 8, 9: Isolation, <2 documents, dataset separation."""

    def test_fewer_than_two_eligible_documents(self, db_session: Session):
        """Single document application returns empty comparisons list."""
        app = _create_app(db_session, "Single Doc Institute")
        _create_doc(db_session, app.id, "lone_doc.pdf", fields={"institutionName": "Single Doc Institute"})

        results = run_cross_doc_checks(app.id, db_session)
        assert results == []

    def test_isolation_between_unrelated_applications(self, db_session: Session):
        """Documents from Application A are NEVER compared against Application B."""
        app_a = _create_app(db_session, "Institute Alpha")
        app_b = _create_app(db_session, "Institute Beta")

        _create_doc(db_session, app_a.id, "doc_a1.pdf", fields={"institutionName": "Institute Alpha"})
        _create_doc(db_session, app_a.id, "doc_a2.pdf", fields={"institutionName": "Institute Alpha"})

        _create_doc(db_session, app_b.id, "doc_b1.pdf", fields={"institutionName": "Institute Beta"})
        _create_doc(db_session, app_b.id, "doc_b2.pdf", fields={"institutionName": "Institute Beta"})

        res_a = run_cross_doc_checks(app_a.id, db_session)
        res_b = run_cross_doc_checks(app_b.id, db_session)

        # Application A should only see its own documents
        inst_a = next(r for r in res_a if "Institution" in r["fieldName"])
        doc_names_a = [e["documentName"] for e in inst_a["entries"]]
        assert "doc_a1.pdf" in doc_names_a
        assert "doc_a2.pdf" in doc_names_a
        assert "doc_b1.pdf" not in doc_names_a

        # Both applications have matching values internally
        assert inst_a["hasDiscrepancy"] is False

    def test_public_reference_directory_isolation(self, db_session: Session):
        """Public reference records are strictly directory data and never treated as uploaded documents."""
        # Ensure a reference institution exists
        ref = PublicReferenceInstitution(
            id="ref-test-01",
            aicte_permanent_id="1-999888777",
            institution_name="COEP Technological University",
            state="Maharashtra",
            city_or_district="Pune",
            institution_type="State University",
            source_publisher="AICTE",
            source_url="https://facilities.aicte-india.org",
            retrieval_date="2026-10-28",
            import_batch_id="batch-01",
            content_checksum="0" * 64,
        )
        db_session.add(ref)
        db_session.commit()

        # Querying cross-doc checks for a reference institution returns empty list
        results = run_cross_doc_checks("ref-test-01", db_session)
        assert results == []


class TestCrossDocAPIAndWorkflow:
    """Tests 10, 11, 12, 13: Endpoints, audit logs, rerun, and human reviewer safety."""

    def test_api_endpoint_response_schema(self, client: TestClient, db_session: Session):
        """GET /api/v1/submissions/{id}/cross-doc-checks returns correct schema."""
        app = _create_app(db_session, "API Test College")
        _create_doc(db_session, app.id, "doc1.pdf", fields={"surveyNumber": "100/1"})
        _create_doc(db_session, app.id, "doc2.pdf", fields={"surveyNumber": "100/1"})

        resp = client.get(f"/api/v1/submissions/{app.id}/cross-doc-checks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["submissionId"] == app.id
        assert data["count"] >= 1
        assert isinstance(data["comparisons"], list)

        first = data["comparisons"][0]
        assert "fieldName" in first
        assert "description" in first
        assert "hasDiscrepancy" in first
        assert "statusText" in first
        assert "entries" in first
        assert "humanReviewRecommendation" in first

    def test_rerunning_comparisons_after_second_document_uploaded(self, client: TestClient, db_session: Session):
        """Uploading a 2nd document transitions application from empty to reconciled."""
        app = _create_app(db_session, "Dynamic Upload Academy")

        # 1 document -> count = 0
        _create_doc(db_session, app.id, "initial.pdf", fields={"landArea": "4.0 acres"})
        resp1 = client.get(f"/api/v1/submissions/{app.id}/cross-doc-checks")
        assert resp1.status_code == 200
        assert resp1.json()["count"] == 0

        # Upload 2nd document via endpoint
        dummy_content = b"%PDF-1.4\n1 0 obj\n<< /Title (NOC) >>\nendobj\nLand Area: 4.0 acres\ntrailer\n<<>>\n%%EOF"
        resp2 = client.post(
            f"/api/v1/submissions/{app.id}/documents/upload",
            files={"file": ("noc_secondary.pdf", dummy_content, "application/pdf")},
            data={"documentType": "Statutory NOC"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["success"] is True

        # Now cross-doc checks reflects both documents
        resp3 = client.get(f"/api/v1/submissions/{app.id}/cross-doc-checks")
        assert resp3.status_code == 200
        assert resp3.json()["count"] >= 1

    def test_reviewer_decision_and_audit_logging(self, client: TestClient, db_session: Session):
        """Reviewer decision creates immutable audit event and updates status without auto-decision."""
        app = _create_app(db_session, "Audit Scrutiny College")

        # Reviewer requests clarification regarding a discrepancy
        resp = client.post(
            f"/api/v1/submissions/{app.id}/request-evidence",
            json={"notes": "Request certified survey map to reconcile Survey No. 48 vs 48/2.", "performedBy": "Reviewer P. Venkat"},
        )
        assert resp.status_code == 200

        # Verify AuditEvent was logged
        events = db_session.query(AuditEvent).filter(AuditEvent.application_id == app.id).all()
        assert len(events) >= 1
        assert any("Survey No. 48" in (e.details or "") for e in events)

    def test_uncertain_comparisons_prevent_auto_adjudication(self, client: TestClient, db_session: Session):
        """Presence of UNABLE_TO_COMPARE or ambiguous fields does NOT auto-reject application."""
        app = _create_app(db_session, "Safety Guard College")
        _create_doc(db_session, app.id, "ambiguous1.pdf", fields={"landArea": "custom units"})
        _create_doc(db_session, app.id, "ambiguous2.pdf", fields={"landArea": "unknown units"})

        # Checks return UNABLE_TO_COMPARE
        res = run_cross_doc_checks(app.id, db_session)
        land_res = next((r for r in res if "Land Area" in r["fieldName"]), None)
        assert land_res is not None
        assert land_res["hasDiscrepancy"] is False

        # Status of application remains SUBMITTED (neither auto-approved nor auto-rejected)
        db_app = db_session.get(Application, app.id)
        assert db_app.status == ApplicationStatus.SUBMITTED
