"""Tests for dashboard analytics and dataset mode isolation.

Verifies:
1. Synthetic mode returns simulated demo metrics and findings.
2. Real Data mode returns strict zero/empty submission metrics and isolates authentic records.
3. Reference institutions count is accurately populated in both modes.
4. Submission queries with mode filtering return correct isolation responses.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestAnalyticsDatasetModeIsolation:
    """Verifies analytics and dataset mode contracts."""

    def test_synthetic_metrics_return_demo_values(self, client: TestClient):
        response = client.get("/api/v1/dashboard/metrics?mode=synthetic")
        assert response.status_code == 200
        data = response.json()

        assert data["mode"] == "synthetic"
        assert data["totalSubmissions"] == 30
        assert data["pendingReview"] == 18
        assert data["underReview"] == 7
        assert data["escalated"] == 4
        assert data["approvedThisMonth"] == 12
        assert data["criticalFindings"] == 8
        assert "referenceInstitutions" in data

    def test_real_metrics_strictly_zero_submissions(self, client: TestClient):
        response = client.get("/api/v1/dashboard/metrics?mode=real")
        assert response.status_code == 200
        data = response.json()

        assert data["mode"] == "real"
        assert data["totalSubmissions"] == 0
        assert data["pendingReview"] == 0
        assert data["underReview"] == 0
        assert data["escalated"] == 0
        assert data["approvedThisMonth"] == 0
        assert data["criticalFindings"] == 0
        assert data["referenceInstitutions"] >= 0

    def test_real_submissions_returns_empty_items(self, client: TestClient):
        response = client.get("/api/v1/submissions?mode=real")
        assert response.status_code == 200
        data = response.json()

        assert data["mode"] == "real"
        assert data["total"] == 0
        assert data["items"] == []
        assert "not been connected" in data.get("message", "")

    def test_reference_data_institutions_accessible(self, client: TestClient):
        response = client.get("/api/v1/reference-data/institutions?limit=20")
        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert "total" in data
        assert data["total"] >= 10
        # Check first institution has official AICTE Permanent ID
        first = data["items"][0]
        assert "aictePermanentId" in first
        assert "institutionName" in first
        assert "state" in first

