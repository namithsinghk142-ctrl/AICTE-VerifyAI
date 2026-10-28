"""Tests for reviewer authentication routes, Google OAuth, allowlist, registration, and session management."""

from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AccountAllowlist, Reviewer
from app.services.auth import (
    hash_password,
    is_email_approved,
    seed_reviewer_accounts,
    verify_password,
)


@pytest.fixture(autouse=True)
def _seed_reviewers(db_session: Session) -> None:
    """Ensure baseline reviewer accounts and allowlist are seeded in test db."""
    seed_reviewer_accounts(db_session)


class TestAuthRoutesOpenAPI:
    """Ensure required authentication routes are exposed in OpenAPI schema."""

    def test_openapi_schema_contains_all_auth_routes(self, client: TestClient) -> None:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        paths = schema.get("paths", {})

        # Assert all auth routes are registered under /api/v1/auth
        for route_name, method in [
            ("/api/v1/auth/login", "post"),
            ("/api/v1/auth/google", "post"),
            ("/api/v1/auth/register", "post"),
            ("/api/v1/auth/logout", "post"),
            ("/api/v1/auth/me", "get"),
            ("/api/v1/auth/config", "get"),
        ]:
            assert route_name in paths, f"{route_name} missing from OpenAPI schema"
            assert method in paths[route_name], f"{method.upper()} {route_name} missing"


class TestAuthConfig:
    """Test auth configuration endpoint."""

    def test_get_auth_config(self, client: TestClient) -> None:
        resp = client.get("/api/v1/auth/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "authMethods" in data
        assert "google" in data["authMethods"]
        assert "email_password" in data["authMethods"]
        assert data["registrationEnabled"] is True


class TestAllowlistAndPriyaRemoval:
    """Test administrator allowlist enforcement and removal of Priya demo account."""

    def test_priya_demo_account_cannot_authenticate(self, client: TestClient) -> None:
        """Priya's legacy demo account must no longer be able to log in."""
        resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": "priya.venkataraman@aicte-verifyai.demo",
                "password": "VerifyAI@Demo2026!",
            },
        )
        assert resp.status_code == 401
        assert "verifyai_token" not in resp.cookies

    def test_priya_not_in_allowlist(self, db_session: Session) -> None:
        approved, _ = is_email_approved("priya.venkataraman@aicte-verifyai.demo", db_session)
        assert approved is False

    def test_approved_accounts_in_allowlist(self, db_session: Session) -> None:
        """Both approved emails must be in the allowlist."""
        for email in ["adhav.sri123@gmail.com", "namithsceptile142@gmail.com"]:
            approved, role = is_email_approved(email, db_session)
            assert approved is True
            assert "Reviewer" in role


class TestEmailPasswordLogin:
    """Test secure email/password login behavior."""

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

    def test_login_invalid_password(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "adhav.sri123@gmail.com", "password": "WrongPassword123!"},
        )
        assert resp.status_code == 401
        assert "verifyai_token" not in resp.cookies

    def test_login_unapproved_email_rejected(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "unapproved.hacker@example.com", "password": "AnyPassword123!"},
        )
        assert resp.status_code == 401
        assert "verifyai_token" not in resp.cookies


class TestGoogleOAuth:
    """Test Google OAuth 2.0 / OpenID Connect token verification and allowlist enforcement."""

    def test_google_login_success_approved_adhav(self, client: TestClient) -> None:
        # Mock Google token for approved email: mock-google-token:email:verified:audience
        token = "mock-google-token:adhav.sri123@gmail.com:true:test-client"
        resp = client.post(
            "/api/v1/auth/google",
            json={"credential": token, "clientId": "test-client"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "adhav.sri123@gmail.com"
        assert data["name"] == "Adhavan S"
        assert "verifyai_token" in resp.cookies

    def test_google_login_success_approved_namith(self, client: TestClient) -> None:
        token = "mock-google-token:namithsceptile142@gmail.com:true:test-client"
        resp = client.post(
            "/api/v1/auth/google",
            json={"credential": token, "clientId": "test-client"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "namithsceptile142@gmail.com"
        assert data["name"] == "Namith Singh"
        assert data["role"] == "Senior Compliance Reviewer"
        assert "verifyai_token" in resp.cookies

    def test_google_login_unapproved_account_rejected(self, client: TestClient) -> None:
        token = "mock-google-token:unapproved.user@gmail.com:true:test-client"
        resp = client.post(
            "/api/v1/auth/google",
            json={"credential": token, "clientId": "test-client"},
        )
        assert resp.status_code == 403
        assert "verifyai_token" not in resp.cookies
        assert "Access restricted" in resp.json()["detail"]

    def test_google_login_unverified_email_rejected(self, client: TestClient) -> None:
        token = "mock-google-token:adhav.sri123@gmail.com:false:test-client"
        resp = client.post(
            "/api/v1/auth/google",
            json={"credential": token, "clientId": "test-client"},
        )
        assert resp.status_code == 400
        assert "verifyai_token" not in resp.cookies
        assert "not verified" in resp.json()["detail"]

    def test_google_login_empty_credential_rejected(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/auth/google",
            json={"credential": "   "},
        )
        assert resp.status_code == 400


class TestRegistration:
    """Test reviewer account registration and pending access state."""

    def test_registration_unapproved_email_creates_pending_no_session(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "pending.applicant@example.com",
                "password": "SecurePassword123!",
                "name": "Pending Applicant",
            },
        )
        # Unapproved registrations receive 403 Forbidden with pending explanation
        assert resp.status_code == 403
        assert "verifyai_token" not in resp.cookies
        assert "pending administrator approval" in resp.json()["detail"]

        # Verify they cannot log in
        login_resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": "pending.applicant@example.com",
                "password": "SecurePassword123!",
            },
        )
        assert login_resp.status_code == 401
        assert "verifyai_token" not in login_resp.cookies

    def test_registration_weak_password_rejected(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "adhav.sri123@gmail.com",
                "password": "short",
                "name": "Test User",
            },
        )
        assert resp.status_code == 422 or resp.status_code == 403

    def test_role_cannot_be_self_assigned(self, client: TestClient, db_session: Session) -> None:
        # Add a temporary test email to allowlist with specific role
        db_session.add(AccountAllowlist(
            email="test.reviewer@example.com",
            assigned_role="Senior Compliance Reviewer",
            is_approved=True,
        ))
        db_session.commit()

        # Registration payload does NOT accept role, backend controls role
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test.reviewer@example.com",
                "password": "SecurePassword123!",
                "name": "Test Reviewer",
                "role": "SuperAdministrator",  # User attempting privilege escalation
            },
        )
        assert resp.status_code == 200
        # Role must be what was assigned in the allowlist, not user input!
        assert resp.json()["role"] == "Senior Compliance Reviewer"


class TestSessionAndLogout:
    """Test session restoration and logout."""

    def test_auth_me_unauthenticated(self, client: TestClient) -> None:
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_auth_me_session_restoration(self, client: TestClient) -> None:
        email = "adhav.sri123@gmail.com"
        password = os.environ.get("VERIFYAI_ADHAV_PASSWORD", "VerifyAI@Adhav123!")
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_resp.status_code == 200

        me_resp = client.get("/api/v1/auth/me")
        assert me_resp.status_code == 200
        data = me_resp.json()
        assert data["email"] == "adhav.sri123@gmail.com"

    def test_auth_logout(self, client: TestClient) -> None:
        email = "adhav.sri123@gmail.com"
        password = os.environ.get("VERIFYAI_ADHAV_PASSWORD", "VerifyAI@Adhav123!")
        client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )

        logout_resp = client.post("/api/v1/auth/logout")
        assert logout_resp.status_code == 200

        me_resp = client.get("/api/v1/auth/me")
        assert me_resp.status_code == 401


class TestReviewerSeedingSafety:
    """Ensure reviewer seeding preserves custom passwords and maintains allowlist."""

    def test_seeding_is_idempotent_and_preserves_custom_password(self, db_session: Session) -> None:
        reviewer = db_session.query(Reviewer).filter(
            Reviewer.email == "adhav.sri123@gmail.com"
        ).first()
        assert reviewer is not None
        original_hash = reviewer.password_hash

        # Run seeding again
        seed_reviewer_accounts(db_session)

        reviewer_after = db_session.query(Reviewer).filter(
            Reviewer.email == "adhav.sri123@gmail.com"
        ).first()
        assert reviewer_after is not None
        assert reviewer_after.password_hash == original_hash

        all_active = db_session.query(Reviewer).filter(Reviewer.is_active == True).all()
        active_emails = {r.email for r in all_active}
        assert "adhav.sri123@gmail.com" in active_emails
        assert "namithsceptile142@gmail.com" in active_emails
        assert "priya.venkataraman@aicte-verifyai.demo" not in active_emails
