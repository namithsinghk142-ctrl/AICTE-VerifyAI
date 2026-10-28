"""Authentication routes for AICTE VerifyAI: Google OAuth, secure login, registration, and session management."""

from __future__ import annotations

import os
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Reviewer
from app.schemas import (
    AuthConfigResponse,
    GoogleLoginPayload,
    LoginPayload,
    RegisterPayload,
    ReviewerProfileResponse,
)
from app.services.auth import (
    TOKEN_TTL_SECONDS,
    authenticate_google_user,
    generate_token,
    is_email_approved,
    register_reviewer,
    verify_password,
    verify_token,
)

router = APIRouter(tags=["Authentication"])

TOKEN_COOKIE = "verifyai_token"
_SECURE_COOKIE = os.environ.get("VERIFYAI_SECURE_COOKIE", "false").lower() == "true"


def _format_reviewer(reviewer: Reviewer) -> dict:
    return {
        "id": reviewer.id,
        "name": reviewer.name,
        "role": reviewer.role,
        "avatarInitials": reviewer.avatar_initials,
        "assignedCount": reviewer.assigned_count,
        "resolvedThisMonth": reviewer.resolved_this_month,
        "email": reviewer.email,
        "authProvider": getattr(reviewer, "auth_provider", "local"),
    }


def _extract_token(request: Request) -> str | None:
    token = request.cookies.get(TOKEN_COOKIE)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
    return token


def get_current_reviewer(request: Request, db: Session = Depends(get_db)) -> Reviewer:
    """Dependency to retrieve and validate the authenticated reviewer.

    Validates session token, active status, and administrator allowlist approval.
    """
    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )

    reviewer_id = verify_token(token)
    if not reviewer_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid or expired.",
        )

    reviewer = db.query(Reviewer).filter(Reviewer.id == reviewer_id).first()
    if not reviewer or not reviewer.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Reviewer account not found or deactivated.",
        )

    is_approved, _ = is_email_approved(reviewer.email, db)
    if not is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access revoked. Account is no longer in the approved allowlist.",
        )

    return reviewer


@router.get(
    "/config",
    response_model=AuthConfigResponse,
    summary="Public authentication configuration",
    description="Returns public OAuth configuration and enabled authentication methods.",
)
def get_auth_config():
    settings = get_settings()
    return {
        "googleClientId": settings.google_client_id,
        "googleAuthEnabled": bool(settings.google_client_id),
        "authMethods": ["google", "email_password"],
        "registrationEnabled": True,
    }


@router.post(
    "/login",
    response_model=ReviewerProfileResponse,
    summary="Reviewer email/password login",
    description="Validate reviewer credentials, verify allowlist approval, set session cookie.",
)
def login(payload: LoginPayload, response: Response, db: Session = Depends(get_db)):
    normalized_email = payload.email.strip().lower()
    reviewer = db.query(Reviewer).filter(Reviewer.email == normalized_email).first()

    # Constant-time path: always call verify_password even when not found
    stored_hash = reviewer.password_hash if reviewer else "invalid$hash"
    valid = verify_password(payload.password, stored_hash)

    # Allowlist verification
    is_approved, _ = is_email_approved(normalized_email, db)

    if not valid or reviewer is None or not reviewer.is_active or not is_approved:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or unauthorized account. Access is restricted to approved reviewers.",
        )

    token = generate_token(reviewer.id)

    response.set_cookie(
        key=TOKEN_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=_SECURE_COOKIE,
        max_age=TOKEN_TTL_SECONDS,
        path="/",
    )

    return _format_reviewer(reviewer)


@router.post(
    "/google",
    response_model=ReviewerProfileResponse,
    summary="Google OAuth / OpenID Connect sign-in",
    description="Verify Google identity token, validate allowlist access, set session cookie.",
)
def google_login(payload: GoogleLoginPayload, response: Response, db: Session = Depends(get_db)):
    reviewer = authenticate_google_user(db, payload.credential, payload.client_id)

    token = generate_token(reviewer.id)

    response.set_cookie(
        key=TOKEN_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=_SECURE_COOKIE,
        max_age=TOKEN_TTL_SECONDS,
        path="/",
    )

    return _format_reviewer(reviewer)


@router.post(
    "/register",
    response_model=ReviewerProfileResponse,
    summary="Reviewer account registration",
    description="Register account with work email. If not in approved allowlist, access remains pending.",
)
def register(payload: RegisterPayload, response: Response, db: Session = Depends(get_db)):
    reviewer, success, message = register_reviewer(
        db=db,
        email=payload.email,
        password=payload.password,
        name=payload.name,
    )

    if not success or reviewer is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message,
        )

    token = generate_token(reviewer.id)

    response.set_cookie(
        key=TOKEN_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=_SECURE_COOKIE,
        max_age=TOKEN_TTL_SECONDS,
        path="/",
    )

    return _format_reviewer(reviewer)


@router.post(
    "/logout",
    summary="Reviewer logout",
    description="Clear reviewer session cookie.",
)
def logout(response: Response):
    response.delete_cookie(key=TOKEN_COOKIE, path="/", samesite="lax")
    return {"detail": "Logged out successfully."}


@router.get(
    "/me",
    response_model=ReviewerProfileResponse,
    summary="Current authenticated reviewer",
    description="Return the authenticated reviewer profile by validating session cookie or bearer token.",
)
def get_auth_me(reviewer: Reviewer = Depends(get_current_reviewer)):
    return _format_reviewer(reviewer)
