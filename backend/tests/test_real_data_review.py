"""Tests for Real-Data Institutional Review Workflow, Dossier, and Audit Trail."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import PublicReferenceInstitution, Application, AuditEvent, ValidationFinding, ReviewerNote


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_real_institution_dossier_lifecycle(client: TestClient):
    db = SessionLocal()
    try:
        ref_inst = db.query(PublicReferenceInstitution).first()
        assert ref_inst is not None

        # 1. Fetch dossier
        res = client.get(f"/api/v1/reference-data/institutions/{ref_inst.id}/dossier")
        assert res.status_code == 200
        dossier = res.json()

        assert dossier["institution"]["aictePermanentId"] == ref_inst.aicte_permanent_id
        assert dossier["applicationCase"]["reviewStatus"] in ["pending_review", "approved", "escalated", "rejected", "under_review"]
        assert len(dossier["findings"]) >= 3
        assert len(dossier["auditEvents"]) >= 1

        # 2. Add reviewer note
        note_res = client.post(
            f"/api/v1/reference-data/institutions/{ref_inst.id}/note",
            json={
                "actor": "Lead Reviewer",
                "role": "Senior Compliance Reviewer",
                "text": "Land documents cross-referenced with Karnataka State Revenue Registry.",
                "category": "scrutiny_dossier",
            },
        )
        assert note_res.status_code == 200
        updated_dossier = note_res.json()
        assert any("Karnataka State Revenue" in n["text"] for n in updated_dossier["reviewerNotes"])

        # 3. Update finding status
        f_id = updated_dossier["findings"][0]["id"]
        find_res = client.post(
            f"/api/v1/reference-data/institutions/{ref_inst.id}/finding-status",
            json={
                "finding_id": f_id,
                "status": "confirmed",
                "actor": "Lead Reviewer",
            },
        )
        assert find_res.status_code == 200
        find_data = find_res.json()
        assert any(f["id"] == f_id and f["reviewStatus"] == "confirmed" for f in find_data["findings"])

        # 4. Execute Scrutiny Action
        act_res = client.post(
            f"/api/v1/reference-data/institutions/{ref_inst.id}/action",
            json={
                "action": "verify",
                "actor": "Lead Reviewer",
                "notes": "All statutory norms under AICTE APH 2024-2027 confirmed.",
            },
        )
        assert act_res.status_code == 200
        final_dossier = act_res.json()
        assert final_dossier["applicationCase"]["reviewStatus"] == "approved"

        # 5. Verify AuditEvent persisted in database
        audit_events = final_dossier["auditEvents"]
        assert any(e["eventType"] == "INSTITUTIONAL_SCRUTINY_APPROVED" for e in audit_events)

        # 6. Verify PublicReferenceInstitution is immutable
        db_ref = db.get(PublicReferenceInstitution, ref_inst.id)
        assert db_ref.approval_status == ref_inst.approval_status
        assert db_ref.aicte_permanent_id == ref_inst.aicte_permanent_id

    finally:
        # Clean up created application case so other tests run on clean state
        app_case = db.query(Application).filter(Application.source_record_id == ref_inst.id).first()
        if app_case:
            db.query(ValidationFinding).filter(ValidationFinding.application_id == app_case.id).delete()
            db.query(AuditEvent).filter(AuditEvent.application_id == app_case.id).delete()
            db.query(ReviewerNote).filter(ReviewerNote.application_id == app_case.id).delete()
            db.delete(app_case)
            db.commit()
        db.close()
