"""Reviewer authentication and account seeding service."""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional

from sqlalchemy.orm import Session

# Re-use standard authentication functions from existing auth module
try:
    from auth import (
        TOKEN_TTL_SECONDS,
        generate_token,
        hash_password,
        verify_password,
        verify_token,
    )
except ImportError:
    try:
        from backend.auth import (
            TOKEN_TTL_SECONDS,
            generate_token,
            hash_password,
            verify_password,
            verify_token,
        )
    except ImportError:
        # Fallback pure-python implementation if backend/auth.py is unreachable
        import hashlib
        import hmac
        import secrets
        import time
        import base64

        _SIGNING_SECRET: str = os.environ.get(
            "VERIFYAI_TOKEN_SECRET",
            "sih-verifyai-dev-secret-do-not-use-in-production-2026",
        )
        TOKEN_TTL_SECONDS = 8 * 60 * 60

        def hash_password(plaintext: str) -> str:
            salt = secrets.token_hex(16)
            dk = hashlib.pbkdf2_hmac(
                "sha256",
                plaintext.encode("utf-8"),
                salt.encode("utf-8"),
                iterations=260_000,
            )
            return f"{salt}${dk.hex()}"

        def verify_password(plaintext: str, stored_hash: str) -> bool:
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
            expires_at = int(time.time()) + TOKEN_TTL_SECONDS
            payload = f"{reviewer_id}:{expires_at}"
            sig = hmac.new(
                _SIGNING_SECRET.encode("utf-8"),
                payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            encoded_payload = base64.urlsafe_b64encode(payload.encode()).decode()
            return f"{encoded_payload}.{sig}"

        def verify_token(token: str) -> Optional[str]:
            try:
                encoded_payload, sig = token.rsplit(".", 1)
                payload = base64.urlsafe_b64decode(encoded_payload.encode()).decode()
                reviewer_id, expires_at_str = payload.split(":", 1)
                expires_at = int(expires_at_str)
            except Exception:
                return None
            expected_sig = hmac.new(
                _SIGNING_SECRET.encode("utf-8"),
                payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected_sig, sig):
                return None
            if int(time.time()) > expires_at:
                return None
            return reviewer_id

from app.models import Reviewer

logger = logging.getLogger("aicte_verifyai.auth")


def seed_reviewer_accounts(db: Session) -> list[Reviewer]:
    """Safely ensure standard demo reviewer accounts exist without overwriting or deleting any existing account.

    Requirements satisfied:
    - Preserves all pre-existing reviewer accounts and their passwords.
    - Checks whether an email already exists before inserting.
    - If an account exists, does not overwrite or reset its password.
    - Creates the additional demo reviewer account (adhav.sri123@gmail.com).
    - Hashed passwords using PBKDF2-HMAC-SHA256 (never stored plaintext).
    """
    priya_email = os.environ.get(
        "VERIFYAI_DEMO_EMAIL", "priya.venkataraman@aicte-verifyai.demo"
    ).strip().lower()
    priya_password = os.environ.get("VERIFYAI_DEMO_PASSWORD", "VerifyAI@Demo2026")

    adhav_email = os.environ.get(
        "VERIFYAI_ADHAV_EMAIL", "adhav.sri123@gmail.com"
    ).strip().lower()
    adhav_password = os.environ.get("VERIFYAI_ADHAV_PASSWORD", "VerifyAI@Adhav123!")

    candidates = [
        {
            "id": "rev-001",
            "email": priya_email,
            "password": priya_password,
            "name": "Priya Venkataraman",
            "role": "Senior Compliance Reviewer",
            "avatar_initials": "PV",
            "assigned_count": 12,
            "resolved_this_month": 34,
        },
        {
            "id": "rev-002",
            "email": adhav_email,
            "password": adhav_password,
            "name": "Adhavan S",
            "role": "Senior Compliance Reviewer",
            "avatar_initials": "AS",
            "assigned_count": 8,
            "resolved_this_month": 22,
        },
    ]

    result: list[Reviewer] = []
    for candidate in candidates:
        existing = db.query(Reviewer).filter(
            Reviewer.email == candidate["email"]
        ).first()

        if existing is None:
            # Check if ID exists to avoid PK clash
            existing_by_id = db.query(Reviewer).filter(
                Reviewer.id == candidate["id"]
            ).first()
            if existing_by_id is not None:
                import uuid
                candidate_id = f"rev-{uuid.uuid4().hex[:6]}"
            else:
                candidate_id = candidate["id"]

            new_reviewer = Reviewer(
                id=candidate_id,
                email=candidate["email"],
                password_hash=hash_password(candidate["password"]),
                name=candidate["name"],
                role=candidate["role"],
                avatar_initials=candidate["avatar_initials"],
                assigned_count=candidate["assigned_count"],
                resolved_this_month=candidate["resolved_this_month"],
                is_active=True,
            )
            db.add(new_reviewer)
            result.append(new_reviewer)
            logger.info("Created reviewer account: %s (%s)", candidate["email"], candidate_id)
        else:
            # Account already exists: DO NOT overwrite password or reset any fields
            result.append(existing)
            logger.info("Preserved existing reviewer account: %s", candidate["email"])

    db.commit()
    return result


if __name__ == "__main__":
    from app.database import SessionLocal, engine, Base, ensure_schema_compatibility
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility(engine)
    with SessionLocal() as session:
        accounts = seed_reviewer_accounts(session)
        print(f"Seeded/verified {len(accounts)} reviewer accounts successfully.")
