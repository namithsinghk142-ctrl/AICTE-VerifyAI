import os
import sys

# Ensure backend package can be imported whether run from root or backend dir
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.auth import hash_password, verify_password, generate_token, verify_token
from backend.database import get_db
from backend.seed_data import seed_reviewer_accounts

client = TestClient(app)

def test_password_hashing():
    pw = "TestSecret!2026"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_token_generation_and_verification():
    reviewer_id = "rev-001"
    token = generate_token(reviewer_id)
    assert token is not None
    verified_id = verify_token(token)
    assert verified_id == reviewer_id

    # Tampered token
    tampered = token[:-4] + "abcd"
    assert verify_token(tampered) is None

def test_auth_login_adhav_success():
    # Ensure seeded
    db = next(get_db())
    seed_reviewer_accounts(db)
    db.close()

    adhav_email = "adhav.sri123@gmail.com"
    adhav_password = os.environ.get("VERIFYAI_ADHAV_PASSWORD", "VerifyAI@Adhav123!")

    response = client.post(
        "/api/v1/auth/login",
        json={"email": adhav_email, "password": adhav_password},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "Adhavan S"
    assert data["role"] == "Senior Compliance Reviewer"
    assert "verifyai_token" in response.cookies


def test_existing_reviewer_priya_cannot_login():
    db = next(get_db())
    seed_reviewer_accounts(db)
    db.close()

    priya_email = "priya.venkataraman@aicte-verifyai.demo"
    priya_password = os.environ.get("VERIFYAI_DEMO_PASSWORD", "VerifyAI@Demo2026")

    response = client.post(
        "/api/v1/auth/login",
        json={"email": priya_email, "password": priya_password},
    )
    assert response.status_code == 401, "Priya demo account must not be able to log in"
    assert "verifyai_token" not in response.cookies


def test_auth_login_invalid_password():
    adhav_email = "adhav.sri123@gmail.com"
    response = client.post(
        "/api/v1/auth/login",
        json={"email": adhav_email, "password": "WrongPassword123"},
    )
    assert response.status_code == 401
    assert "verifyai_token" not in response.cookies


def test_auth_login_unknown_user():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@aicte.gov.in", "password": "AnyPassword"},
    )
    assert response.status_code == 401


def test_auth_me_authenticated_and_unauthenticated():
    # Fresh unauthenticated client -> 401
    fresh_client = TestClient(app)
    unauth_resp = fresh_client.get("/api/v1/auth/me")
    assert unauth_resp.status_code == 401

    # Login with Adhav account and verify /auth/me returns 200
    adhav_email = "adhav.sri123@gmail.com"
    adhav_password = os.environ.get("VERIFYAI_ADHAV_PASSWORD", "VerifyAI@Adhav123!")
    login_resp = fresh_client.post(
        "/api/v1/auth/login",
        json={"email": adhav_email, "password": adhav_password},
    )
    assert login_resp.status_code == 200

    me_resp = fresh_client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["name"] == "Adhavan S"

    # Logout and verify /auth/me returns 401 again
    logout_resp = fresh_client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 200
    post_logout = fresh_client.get("/api/v1/auth/me")
    assert post_logout.status_code == 401


if __name__ == "__main__":
    test_password_hashing()
    test_token_generation_and_verification()
    test_auth_login_adhav_success()
    test_existing_reviewer_priya_cannot_login()
    test_auth_login_invalid_password()
    test_auth_login_unknown_user()
    test_auth_me_authenticated_and_unauthenticated()
    print("ALL AUTH TESTS PASSED PERFECTLY!")

