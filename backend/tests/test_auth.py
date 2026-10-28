"""Tests for reviewer authentication routes and account seeding in AICTE VerifyAI."""

from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Reviewer
from app.services.auth import (
    hash_password,
    seed_reviewer_accounts,
    verify_password,
)


@pytest.fixture(autouse=True)
def _seed_reviewers(db_session: Session) -> None:
    """Ensure baseline reviewer accounts are seeded in test db."""
    seed_reviewer_accounts(db_session)


class TestAuthRoutesOpenAPI:
    """Ensure required authentication routes are exposed in OpenAPI schema."""

    def test_openapi_schema_contains_all_three_auth_routes(self, client: TestClient) -> None:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        paths = schema.get("paths", {})

        # Assert all 3 routes required by frontend are registered
        assert "/api/v1/auth/login" in paths, "POST /api/v1/auth/login missing from OpenAPI"
        assert "post" in paths["/api/v1/auth/login"]

        assert "/api/v1/auth/logout" in paths, "POST /api/v1/auth/logout missing from OpenAPI"
        assert "post" in paths["/api/v1/auth/logout"]

        assert "/api/v1/auth/me" in paths, "GET /api/v1/auth/me missing from OpenAPI"
        assert "get" in paths["/api/v1/auth/me"]


class TestAuthEndpoints:
    """Test login, logout, and session restoration on active backend."""

    def test_login_success_adhav_account(self, client: TestClient) -> None:
        email = "adhav.sri123@gmail.com"
        password = os.environ.get("VERIFYAI_ADHAV_PASSWORD", "VerifyAI@Adhav123!")

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Adhavan S"
        assert data["role"] == "Senior Compliance Reviewer"
        assert data["avatarInitials"] == "AS"
        assert "verifyai_token" in resp.cookies

    def test_login_existing_reviewer_account_intact(self, client: TestClient) -> None:
        email = "priya.venkataraman@aicte-verifyai.demo"
        password = os.environ.get("VERIFYAI_DEMO_PASSWORD", "VerifyAI@Demo2026")

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Priya Venkataraman"
        assert data["role"] == "Senior Compliance Reviewer"
        assert data["avatarInitials"] == "PV"
        assert "verifyai_token" in resp.cookies

    def test_login_invalid_password(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "adhav.sri123@gmail.com", "password": "WrongPassword123!"},
        )
        assert resp.status_code == 401
        assert "verifyai_token" not in resp.cookies
        assert "Invalid credentials" in resp.json()["detail"]

    def test_login_unknown_email(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@aicte.gov.in", "password": "AnyPassword123!"},
        )
        assert resp.status_code == 401
        assert "verifyai_token" not in resp.cookies

    def test_auth_me_unauthenticated(self, client: TestClient) -> None:
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401
        assert "Not authenticated" in resp.json()["detail"]

    def test_auth_me_session_restoration(self, client: TestClient) -> None:
        # First login to obtain cookie
        email = "adhav.sri123@gmail.com"
        password = os.environ.get("VERIFYAI_ADHAV_PASSWORD", "VerifyAI@Adhav123!")
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_resp.status_code == 200

        # Now call /me using cookie
        me_resp = client.get("/api/v1/auth/me")
        assert me_resp.status_code == 200
        data = me_resp.json()
        assert data["name"] == "Adhavan S"
        assert data["role"] == "Senior Compliance Reviewer"

    def test_auth_logout(self, client: TestClient) -> None:
        # Login
        email = "adhav.sri123@gmail.com"
        password = os.environ.get("VERIFYAI_ADHAV_PASSWORD", "VerifyAI@Adhav123!")
        client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )

        # Logout
        logout_resp = client.post("/api/v1/auth/logout")
        assert logout_resp.status_code == 200
        assert logout_resp.json()["detail"] == "Logged out successfully."

        # Verify /me now fails
        me_resp = client.get("/api/v1/auth/me")
        assert me_resp.status_code == 401


class TestReviewerSeedingSafety:
    """Ensure reviewer seeding does not overwrite or delete existing accounts."""

    def test_seeding_is_idempotent_and_preserves_custom_password(self, db_session: Session) -> None:
        # Verify account exists
        reviewer = db_session.query(Reviewer).filter(
            Reviewer.email == "adhav.sri123@gmail.com"
        ).first()
        assert reviewer is not None
        original_hash = reviewer.password_hash

        # Run seeding again
        seed_reviewer_accounts(db_session)

        # Re-fetch
        reviewer_after = db_session.query(Reviewer).filter(
            Reviewer.email == "adhav.sri123@gmail.com"
        ).first()
        assert reviewer_after is not None
        assert reviewer_after.password_hash == original_hash, "Seeding must NOT overwrite password of existing account"

        # Verify both accounts exist
        all_reviewers = db_session.query(Reviewer).all()
        emails = {r.email for r in all_reviewers}
        assert "adhav.sri123@gmail.com" in emails
        assert "priya.venkataraman@aicte-verifyai.demo" in emails
