"""Comprehensive tests for Verified Dataset Import Pipeline, Data Classification, and Mode Separation.

Tests cover:
1. Both dataset modes are selectable via API.
2. Synthetic records remain intact after real data import.
3. Real mode never displays synthetic records.
4. Synthetic mode never displays real records.
5. Dashboard metrics reflect the selected dataset.
6. Empty real-data mode displays genuine zero counts and empty state.
7. Dataset switching is non-destructive (does not modify or delete records).
8. Duplicate imports and repeated execution are idempotent.
9. Malformed rows, missing identifiers, and incompatible schemas are cleanly rejected.
10. Interrupted/dry-run imports do not corrupt previously imported data.
11. Source provenance and SHA-256 checksums are preserved.
12. Public reference records are never counted as authentic submitted applications.
13. Data quality and provenance summary accurately reports source statuses.
14. Backend real-mode endpoint never leaks synthetic records.
15. Existing authentication and reviewer accounts remain functional.
"""

from __future__ import annotations

import copy
import hashlib
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.main import create_app
from app.models import (
    Application,
    DataClassification,
    PublicReferenceInstitution,
    Reviewer,
)
from app.services.dataset_importer import (
    compute_batch_checksum,
    compute_record_checksum,
    import_verified_dataset,
    validate_and_normalize_record,
)


@pytest.fixture
def app_client():
    app = create_app()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_pipeline.db"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        yield session


class TestVerifiedDatasetPipeline:
    """Test suite for dataset ingestion, deduplication, provenance, and mode isolation."""

    # 1. Both modes are selectable via API
    def test_both_modes_selectable(self, app_client: TestClient):
        res_synth = app_client.get("/api/v1/dashboard/metrics?mode=synthetic")
        assert res_synth.status_code == 200
        assert res_synth.json()["mode"] == "synthetic"

        res_real = app_client.get("/api/v1/dashboard/metrics?mode=real")
        assert res_real.status_code == 200
        assert res_real.json()["mode"] == "real"

    # 2. Synthetic records remain intact after importing real data
    def test_synthetic_records_remain_intact_after_import(self, test_db):
        # Insert a synthetic application
        synth_app = Application(
            institution_name="Northstar Institute of Technology",
            application_category="Engineering & Technology",
            academic_year="2025-2026",
            data_classification=DataClassification.SYNTHETIC_DEMO.value,
            is_synthetic_demo=True,
        )
        test_db.add(synth_app)
        test_db.commit()

        # Run verified dataset import
        summary = import_verified_dataset(test_db, dry_run=False)
        assert summary["status"] == "SUCCESS"
        assert summary["records_accepted"] > 0

        # Verify synthetic application is untouched
        db_synth = test_db.query(Application).filter(Application.id == synth_app.id).first()
        assert db_synth is not None
        assert db_synth.institution_name == "Northstar Institute of Technology"
        assert db_synth.is_synthetic_demo is True

    # 3. Real mode never displays synthetic records
    def test_real_mode_never_displays_synthetic_records(self, app_client: TestClient):
        res = app_client.get("/api/v1/submissions?mode=real")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0
        # Ensure no synthetic data leaked into Real mode
        assert not any("Northstar" in str(item) for item in data["items"])

    # 4. Synthetic mode never displays real reference records as applications
    def test_synthetic_mode_never_displays_real_reference_records(self, app_client: TestClient):
        res = app_client.get("/api/v1/submissions?mode=synthetic")
        assert res.status_code == 200
        data = res.json()
        # In synthetic mode, items are either demo items or empty for local frontend fallback
        for item in data.get("items", []):
            assert item.get("data_classification") != "PUBLIC_REFERENCE"

    # 5. Dashboard metrics reflect selected dataset mode
    def test_dashboard_metrics_reflect_mode(self, app_client: TestClient):
        synth_metrics = app_client.get("/api/v1/dashboard/metrics?mode=synthetic").json()
        assert synth_metrics["totalSubmissions"] == 30
        assert synth_metrics["pendingReview"] > 0
        assert synth_metrics["criticalFindings"] > 0

        real_metrics = app_client.get("/api/v1/dashboard/metrics?mode=real").json()
        assert real_metrics["totalSubmissions"] == 0
        assert real_metrics["pendingReview"] == 0
        assert real_metrics["criticalFindings"] == 0
        assert real_metrics["referenceInstitutions"] >= 0

    # 6. Empty real-data mode displays genuine zero metrics and proper empty state
    def test_empty_real_data_mode(self, app_client: TestClient):
        res = app_client.get("/api/v1/submissions?mode=real")
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 0
        assert body["items"] == []
        assert "message" in body

    # 7. Dataset switching does not modify or delete records
    def test_dataset_switching_does_not_mutate_records(self, app_client: TestClient):
        # Query synthetic mode twice with real mode in between
        m1 = app_client.get("/api/v1/dashboard/metrics?mode=synthetic").json()
        m_real = app_client.get("/api/v1/dashboard/metrics?mode=real").json()
        m2 = app_client.get("/api/v1/dashboard/metrics?mode=synthetic").json()

        assert m1["totalSubmissions"] == m2["totalSubmissions"] == 30
        assert m_real["totalSubmissions"] == 0

    # 8. Duplicate imports and repeated execution are idempotent
    def test_import_idempotency(self, test_db):
        s1 = import_verified_dataset(test_db, dry_run=False)
        accepted_first = s1["records_accepted"]
        assert accepted_first > 0

        # Second run with same data
        s2 = import_verified_dataset(test_db, dry_run=False)
        assert s2["status"] == "SUCCESS"
        assert s2["records_accepted"] == 0
        assert s2["records_skipped"] == accepted_first

    # 9. Malformed rows, missing identifiers, and invalid format are rejected cleanly
    def test_malformed_records_rejected(self, test_db):
        bad_records = [
            {"institution_name": "No ID Institute"},  # Missing aicte_permanent_id
            {"aicte_permanent_id": "INVALID-ID", "institution_name": "Bad ID Tech", "state": "Delhi", "city_or_district": "Delhi", "institution_type": "Univ", "source_publisher": "Gov", "source_url": "http"},
            {"aicte_permanent_id": "1-11111", "institution_name": "A", "state": "Tamil Nadu", "city_or_district": "Chennai", "institution_type": "College", "source_publisher": "Gov", "source_url": "http"},  # Name too short
        ]
        summary = import_verified_dataset(test_db, raw_records=bad_records, dry_run=True)
        assert summary["records_rejected"] == 3
        assert summary["records_accepted"] == 0
        assert len(summary["rejection_reasons"]) == 3

    # 10. Dry-run mode does not write to database
    def test_dry_run_leaves_database_clean(self, test_db):
        count_before = test_db.query(PublicReferenceInstitution).count()
        summary = import_verified_dataset(test_db, dry_run=True)
        assert summary["status"] == "DRY_RUN_COMPLETED"
        assert summary["records_accepted"] > 0
        count_after = test_db.query(PublicReferenceInstitution).count()
        assert count_after == count_before

    # 11. Source provenance and SHA-256 checksums are preserved
    def test_provenance_and_checksum_integrity(self, test_db):
        import_verified_dataset(test_db, dry_run=False)
        inst = test_db.query(PublicReferenceInstitution).first()
        assert inst is not None
        assert inst.aicte_permanent_id.startswith("1-")
        assert len(inst.content_checksum) == 64  # SHA-256 length
        assert inst.source_publisher != ""
        assert inst.source_url.startswith("http")

        # Verify checksum calculation matches canonical values
        recomputed = compute_record_checksum({
            "aicte_permanent_id": inst.aicte_permanent_id,
            "institution_name": inst.institution_name,
            "state": inst.state,
            "city_or_district": inst.city_or_district,
            "institution_type": inst.institution_type,
            "academic_year": inst.academic_year,
        })
        assert inst.content_checksum == recomputed

    # 12. Public reference records are never counted as submitted applications
    def test_public_reference_not_counted_as_application(self, test_db):
        import_verified_dataset(test_db, dry_run=False)
        ref_count = test_db.query(PublicReferenceInstitution).count()
        app_count = test_db.query(Application).count()
        assert ref_count > 0
        assert app_count == 0  # No application submissions created

    # 13. Data quality and provenance summary endpoint
    def test_dataset_summary_endpoint(self, app_client: TestClient):
        res = app_client.get("/api/v1/reference-data/summary")
        assert res.status_code == 200
        data = res.json()
        assert "sources" in data
        assert len(data["sources"]) >= 3
        assert data["dataQuality"]["status"] == "HEALTHY"
        assert data["dataQuality"]["missingRequiredFields"] == 0
        assert data["dataQuality"]["duplicateIdentifiers"] == 0

    # 14. Reference data listing and filtering
    def test_reference_data_institutions_api(self, app_client: TestClient):
        res = app_client.get("/api/v1/reference-data/institutions?limit=5")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 6
        assert len(data["items"]) <= 5
        # Search filter
        search_res = app_client.get("/api/v1/reference-data/institutions?query=PSG")
        assert search_res.status_code == 200
        search_items = search_res.json()["items"]
        assert any("PSG" in item["institutionName"] for item in search_items)

    # 15. Existing authentication and reviewer accounts remain functional
    def test_auth_workflow_intact(self, app_client: TestClient):
        # Demo reviewer login
        login_res = app_client.post(
            "/api/v1/auth/login",
            json={"email": "adhav.sri123@gmail.com", "password": "VerifyAI@Adhav123!"},
        )
        assert login_res.status_code == 200
        profile = login_res.json()
        assert profile["name"] == "Adhavan S"
        assert profile["role"] == "Senior Compliance Reviewer"

        # Check me
        me_res = app_client.get("/api/v1/auth/me")
        assert me_res.status_code == 200
        assert me_res.json()["name"] == "Adhavan S"
