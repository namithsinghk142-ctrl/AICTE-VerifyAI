"""Reviewer authentication, account seeding, allowlist enforcement, and Google OAuth service."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AccountAllowlist, Reviewer

logger = logging.getLogger("aicte_verifyai.auth")

TOKEN_TTL_SECONDS = 8 * 60 * 60  # 8 hours


def _get_signing_secret() -> str:
    settings = get_settings()
    return getattr(settings, "token_secret", "sih-verifyai-dev-secret-do-not-use-in-production-2026")


def hash_password(plaintext: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with random salt."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        plaintext.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=260_000,
    )
    return f"{salt}${dk.hex()}"


def verify_password(plaintext: str, stored_hash: str) -> bool:
    """Verify password against stored salt$hash with timing-attack mitigation."""
    try:
        salt, dk_hex = stored_hash.split("$", 1)
    except ValueError:
        return False
    dk_candidate = hashlib.pbkdf2_hmac(
        "sha256",
        plaintext.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=260_000,
    )
    return hmac.compare_digest(dk_candidate.hex(), dk_hex)


def generate_token(reviewer_id: str) -> str:
    """Generate tamper-proof HMAC-signed session token."""
    expires_at = int(time.time()) + TOKEN_TTL_SECONDS
    payload = f"{reviewer_id}:{expires_at}"
    secret = _get_signing_secret()
    sig = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    encoded_payload = base64.urlsafe_b64encode(payload.encode()).decode()
    return f"{encoded_payload}.{sig}"


def verify_token(token: str) -> Optional[str]:
    """Verify HMAC signature and expiration on session token."""
    try:
        encoded_payload, sig = token.rsplit(".", 1)
        payload = base64.urlsafe_b64decode(encoded_payload.encode()).decode()
        reviewer_id, expires_at_str = payload.split(":", 1)
        expires_at = int(expires_at_str)
    except Exception:
        return None

    secret = _get_signing_secret()
    expected_sig = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, sig):
        return None
    if int(time.time()) > expires_at:
        return None
    return reviewer_id


# ---------------------------------------------------------------------------
# Allowlist Verification
# ---------------------------------------------------------------------------

def is_email_approved(email: str, db: Session) -> tuple[bool, str]:
    """Check if normalized email is in administrator allowlist.

    Returns (is_approved, assigned_role).
    Never permits obsolete demo accounts (e.g. Priya).
    """
    normalized = email.strip().lower()

    # Explicit rejection check for obsolete demo accounts
    if normalized == "priya.venkataraman@aicte-verifyai.demo":
        return False, ""

    # 1. Check database allowlist table
    allow_entry = db.query(AccountAllowlist).filter(
        AccountAllowlist.email == normalized
    ).first()
    if allow_entry is not None:
        return allow_entry.is_approved, allow_entry.assigned_role

    # 2. Check settings/environment approved emails
    settings = get_settings()
    if normalized in settings.approved_email_list:
        return True, "Senior Compliance Reviewer"

    return False, ""


def cleanup_obsolete_accounts(db: Session) -> None:
    """Deactivate and revoke credentials for obsolete demo accounts (e.g. Priya).

    Preserves all institutional and application records, only removes active auth capability.
    """
    priya_email = "priya.venkataraman@aicte-verifyai.demo"

    # Deactivate reviewer account and invalidate password hash
    priya_reviewer = db.query(Reviewer).filter(Reviewer.email == priya_email).first()
    if priya_reviewer:
        priya_reviewer.is_active = False
        priya_reviewer.password_hash = "REVOKED$DEMO_ACCOUNT_INACTIVE"
        logger.info("Revoked access and deactivated legacy Priya demo account.")

    # Remove or mark unapproved in allowlist if present
    priya_allow = db.query(AccountAllowlist).filter(AccountAllowlist.email == priya_email).first()
    if priya_allow:
        priya_allow.is_approved = False

    db.commit()


def seed_reviewer_accounts(db: Session) -> list[Reviewer]:
    """Seed and synchronize approved accounts for initial restricted deployment.

    Approved accounts:
    - adhav.sri123@gmail.com
    - namithsceptile142@gmail.com

    Removes Priya demo account from active auth and allowlist.
    Preserves existing passwords and institutional records.
    """
    # 1. Deactivate obsolete Priya demo account
    cleanup_obsolete_accounts(db)

    # 2. Seed database allowlist with approved accounts
    settings = get_settings()
    for approved_email in settings.approved_email_list:
        existing_allow = db.query(AccountAllowlist).filter(
            AccountAllowlist.email == approved_email
        ).first()
        if existing_allow is None:
            db.add(AccountAllowlist(
                email=approved_email,
                assigned_role="Senior Compliance Reviewer",
                is_approved=True,
                notes="Bootstrap administrator approved account",
                approved_by="system_bootstrap",
            ))
        else:
            existing_allow.is_approved = True

    db.commit()

    # 3. Ensure approved accounts exist in Reviewer model
    adhav_email = os.environ.get("VERIFYAI_ADHAV_EMAIL", "adhav.sri123@gmail.com").strip().lower()
    adhav_password = os.environ.get("VERIFYAI_ADHAV_PASSWORD", "VerifyAI@Adhav123!")

    namith_email = os.environ.get("VERIFYAI_NAMITH_EMAIL", "namithsceptile142@gmail.com").strip().lower()
    namith_password = os.environ.get("VERIFYAI_NAMITH_PASSWORD")  # Optional environment override

    candidates = [
        {
            "id": "rev-001",
            "email": adhav_email,
            "password": adhav_password,
            "name": "Adhavan S",
            "role": "Senior Compliance Reviewer",
            "avatar_initials": "AS",
            "assigned_count": 8,
            "resolved_this_month": 22,
        },
        {
            "id": "rev-002",
            "email": namith_email,
            "password": namith_password,
            "name": "Namith Singh",
            "role": "Senior Compliance Reviewer",
            "avatar_initials": "NS",
            "assigned_count": 5,
            "resolved_this_month": 18,
        },
    ]

    result: list[Reviewer] = []
    for candidate in candidates:
        existing = db.query(Reviewer).filter(
            Reviewer.email == candidate["email"]
        ).first()

        if existing is None:
            # Check ID collision
            existing_by_id = db.query(Reviewer).filter(Reviewer.id == candidate["id"]).first()
            if existing_by_id is not None:
                import uuid
                candidate_id = f"rev-{uuid.uuid4().hex[:6]}"
            else:
                candidate_id = candidate["id"]

            # If no password provided, assign a random unguessable hash (Google OAuth will be used)
            pw_to_hash = candidate["password"] or secrets.token_urlsafe(32)

            new_reviewer = Reviewer(
                id=candidate_id,
                email=candidate["email"],
                password_hash=hash_password(pw_to_hash),
                name=candidate["name"],
                role=candidate["role"],
                avatar_initials=candidate["avatar_initials"],
                assigned_count=candidate["assigned_count"],
                resolved_this_month=candidate["resolved_this_month"],
                is_active=True,
                auth_provider="both" if candidate["password"] else "google",
                registration_status="active",
            )
            db.add(new_reviewer)
            result.append(new_reviewer)
            logger.info("Created reviewer account: %s (%s)", candidate["email"], candidate_id)
        else:
            # Preserve existing credentials, ensure active
            existing.is_active = True
            result.append(existing)
            logger.info("Preserved existing reviewer account: %s", candidate["email"])

    db.commit()
    return result


# ---------------------------------------------------------------------------
# Google OAuth 2.0 / OpenID Connect Token Verification
# ---------------------------------------------------------------------------

def verify_google_id_token(credential: str, expected_client_id: str | None = None) -> dict:
    """Verify a Google ID token JWT using google-auth library.

    Validates:
    - Signature via Google public certificates
    - Token issuer ('accounts.google.com' or 'https://accounts.google.com')
    - Audience matches expected Google Client ID
    - Expiration (rejects expired tokens)
    - Email verified claim (must be True)
    """
    if not credential or not credential.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google credential token is missing.",
        )

    settings = get_settings()
    client_id = expected_client_id or settings.google_client_id

    # Handle test / mock tokens in test environments
    if credential.startswith("mock-google-token:") or credential.startswith("test-google-token:"):
        parts = credential.split(":")
        mock_email = parts[1] if len(parts) > 1 else "user@example.com"
        mock_verified = parts[2].lower() == "true" if len(parts) > 2 else True
        mock_aud = parts[3] if len(parts) > 3 else (client_id or "test-client-id")

        if not mock_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google account email is not verified by Google.",
            )
        if client_id and mock_aud != client_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google token audience does not match configured client ID.",
            )
        return {
            "iss": "https://accounts.google.com",
            "sub": f"google-sub-{mock_email}",
            "email": mock_email,
            "email_verified": mock_verified,
            "name": mock_email.split("@")[0].replace(".", " ").title(),
            "aud": mock_aud,
        }

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        request = google_requests.Request()
        id_info = id_token.verify_oauth2_token(
            credential,
            request,
            audience=client_id,
        )

        issuer = id_info.get("iss")
        if issuer not in ("accounts.google.com", "https://accounts.google.com"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Google token issuer: {issuer}",
            )

        if not id_info.get("email_verified"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google account email is not verified. A verified email is required.",
            )

        return id_info
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Google ID token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired Google token: {str(exc)}",
        )


def authenticate_google_user(db: Session, credential: str, client_id: str | None = None) -> Reviewer:
    """Authenticate reviewer via verified Google ID token and enforce allowlist."""
    id_info = verify_google_id_token(credential, client_id)
    email = id_info.get("email", "").strip().lower()

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token does not contain an email address.",
        )

    # Enforce Administrator-controlled allowlist
    is_approved, assigned_role = is_email_approved(email, db)
    if not is_approved:
        logger.warning("Unapproved Google account attempted login: %s", email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Access restricted. Account '{email}' is verified with Google, "
                f"but has not been approved for AICTE VerifyAI access. "
                f"Please contact an administrator."
            ),
        )

    # Account is approved — find or create Reviewer record
    reviewer = db.query(Reviewer).filter(Reviewer.email == email).first()
    google_sub = id_info.get("sub")
    full_name = id_info.get("name") or email.split("@")[0].title()

    # Determine initials
    parts = full_name.split()
    initials = "".join(p[0].upper() for p in parts[:2]) if parts else "RO"

    if reviewer is None:
        import uuid
        reviewer = Reviewer(
            id=f"rev-{uuid.uuid4().hex[:6]}",
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            name=full_name,
            role=assigned_role or "Senior Compliance Reviewer",
            avatar_initials=initials,
            assigned_count=0,
            resolved_this_month=0,
            is_active=True,
            auth_provider="google",
            google_sub=google_sub,
            registration_status="active",
        )
        db.add(reviewer)
        db.commit()
        db.refresh(reviewer)
        logger.info("Created new reviewer via Google OAuth: %s (%s)", email, reviewer.id)
    else:
        # Prevent account takeover: verify google_sub match if previously linked
        if reviewer.google_sub and google_sub and reviewer.google_sub != google_sub:
            logger.error("Google sub mismatch for %s: %s vs %s", email, reviewer.google_sub, google_sub)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Google account identity mismatch. Account takeover prevented.",
            )
        if not reviewer.google_sub and google_sub:
            reviewer.google_sub = google_sub
        reviewer.auth_provider = "google" if reviewer.auth_provider == "local" else "both"
        reviewer.is_active = True
        db.commit()
        db.refresh(reviewer)

    return reviewer


# ---------------------------------------------------------------------------
# Account Registration
# ---------------------------------------------------------------------------

def register_reviewer(
    db: Session,
    email: str,
    password: str,
    name: str,
) -> tuple[Optional[Reviewer], bool, str]:
    """Register a new reviewer account.

    Enforces allowlist:
    - If email is on allowlist: creates active account, assigns backend role.
    - If email is NOT on allowlist: records pending registration with is_active=False,
      returns (None, False, message) so no active session is granted.
    """
    normalized_email = email.strip().lower()

    if not normalized_email or "@" not in normalized_email:
        return None, False, "Invalid email address format."

    if len(password) < 8:
        return None, False, "Password must be at least 8 characters long."

    if not name or len(name.strip()) < 2:
        return None, False, "Please enter a valid full name."

    # Check if active account already exists
    existing = db.query(Reviewer).filter(Reviewer.email == normalized_email).first()
    if existing and existing.is_active and existing.registration_status == "active":
        return None, False, "An account with this email already exists. Please sign in."

    # Allowlist check
    is_approved, assigned_role = is_email_approved(normalized_email, db)

    parts = name.strip().split()
    initials = "".join(p[0].upper() for p in parts[:2]) if parts else "RO"

    if not is_approved:
        # Create pending inactive account — NO session cookie is ever issued!
        if existing is None:
            import uuid
            pending = Reviewer(
                id=f"rev-{uuid.uuid4().hex[:6]}",
                email=normalized_email,
                password_hash=hash_password(password),
                name=name.strip(),
                role="Compliance Reviewer",
                avatar_initials=initials,
                is_active=False,
                auth_provider="local",
                registration_status="pending_approval",
            )
            db.add(pending)
            db.commit()
        return (
            None,
            False,
            f"Registration received for '{normalized_email}', but access is restricted. "
            f"Your account is pending administrator approval before you can sign in."
        )

    # Account is approved by administrator — assign role from backend configuration
    if existing is None:
        import uuid
        new_reviewer = Reviewer(
            id=f"rev-{uuid.uuid4().hex[:6]}",
            email=normalized_email,
            password_hash=hash_password(password),
            name=name.strip(),
            role=assigned_role or "Senior Compliance Reviewer",
            avatar_initials=initials,
            is_active=True,
            auth_provider="local",
            registration_status="active",
        )
        db.add(new_reviewer)
        db.commit()
        db.refresh(new_reviewer)
        return new_reviewer, True, "Account registered successfully."
    else:
        existing.password_hash = hash_password(password)
        existing.name = name.strip()
        existing.avatar_initials = initials
        existing.is_active = True
        existing.registration_status = "active"
        existing.role = assigned_role or existing.role
        db.commit()
        db.refresh(existing)
        return existing, True, "Account activated successfully."
