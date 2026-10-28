"""Authentication routes for AICTE VerifyAI reviewer login and session management."""

from __future__ import annotations

import os
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Reviewer
from app.schemas import LoginPayload, ReviewerProfileResponse
from app.services.auth import (
    TOKEN_TTL_SECONDS,
    generate_token,
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
    }


def _extract_token(request: Request) -> str | None:
    token = request.cookies.get(TOKEN_COOKIE)
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
    return token


@router.post(
    "/login",
    response_model=ReviewerProfileResponse,
    summary="Reviewer login",
    description="Validate reviewer credentials, set session cookie, and return reviewer profile.",
)
def login(payload: LoginPayload, response: Response, db: Session = Depends(get_db)):
    reviewer = db.query(Reviewer).filter(
        Reviewer.email == payload.email.strip().lower()
    ).first()

    # Constant-time path: always call verify_password even when not found
    # to avoid timing oracle on email enumeration
    stored_hash = reviewer.password_hash if reviewer else "invalid$hash"
    valid = verify_password(payload.password, stored_hash)

    if not valid or reviewer is None or not reviewer.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please check your email and password.",
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
def get_auth_me(request: Request, db: Session = Depends(get_db)):
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
            detail="Reviewer account not found.",
        )

    return _format_reviewer(reviewer)
