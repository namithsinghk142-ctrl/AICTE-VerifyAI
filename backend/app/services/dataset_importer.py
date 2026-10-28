"""Verified Public Dataset Import Pipeline for AICTE VerifyAI.

Safely imports, validates, normalizes, deduplicates, and checksums public reference
institutions from verified AICTE and AISHE directories into the public_reference_institutions table.
Features:
- Strict field validation and malformed row rejection.
- SHA-256 content checksums for data integrity verification.
- Idempotent upserting and deduplication on aicte_permanent_id.
- Safe dry-run mode (--dry-run) without database mutation.
- Clear separation: NEVER touches synthetic demo applications or reviewer data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import PublicReferenceInstitution

logger = logging.getLogger("verifyai.importer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Ensure database tables exist without modifying existing data
Base.metadata.create_all(bind=engine)

DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "aicte_public_reference_institutions_2024_2025.json"
)

AICTE_ID_REGEX = re.compile(r"^1-\d{5,12}$")
REQUIRED_FIELDS = [
    "aicte_permanent_id",
    "institution_name",
    "state",
    "city_or_district",
    "institution_type",
    "source_publisher",
    "source_url",
]


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_record_checksum(record: Dict[str, Any]) -> str:
    """Compute deterministic SHA-256 content checksum from canonical fields."""
    canonical_str = "|".join([
        str(record.get("aicte_permanent_id", "")).strip(),
        str(record.get("institution_name", "")).strip().lower(),
        str(record.get("state", "")).strip().lower(),
        str(record.get("city_or_district", "")).strip().lower(),
        str(record.get("institution_type", "")).strip().lower(),
        str(record.get("academic_year", "2024–2025")).strip(),
    ])
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()


def compute_batch_checksum(records: List[Dict[str, Any]]) -> str:
    """Compute cumulative SHA-256 checksum for an entire import batch."""
    individual_checksums = sorted(compute_record_checksum(r) for r in records)
    combined = ";".join(individual_checksums)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def validate_and_normalize_record(raw: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Validate required fields, types, and format. Return normalized record or failure reason."""
    if not isinstance(raw, dict):
        return None, "Record is not a valid JSON object"

    # Check required fields
    for field in REQUIRED_FIELDS:
        val = raw.get(field)
        if val is None or not str(val).strip():
            return None, f"Missing or empty required field: '{field}'"

    raw_id = str(raw["aicte_permanent_id"]).strip()
    if not AICTE_ID_REGEX.match(raw_id):
        return None, f"Invalid AICTE Permanent ID format: '{raw_id}' (expected format 1-xxxxxxxxx)"

    name = str(raw["institution_name"]).strip()
    if len(name) < 3:
        return None, f"Institution name too short: '{name}'"

    normalized: Dict[str, Any] = {
        "aicte_permanent_id": raw_id,
        "institution_name": name,
        "state": str(raw["state"]).strip(),
        "city_or_district": str(raw["city_or_district"]).strip(),
        "institution_type": str(raw["institution_type"]).strip(),
        "aishe_code": str(raw.get("aishe_code", "")).strip() or None,
        "sponsoring_body": str(raw.get("sponsoring_body", "")).strip() or None,
        "approval_status": str(raw.get("approval_status", "Approved (Public Reference)")).strip(),
        "academic_year": str(raw.get("academic_year", "2024–2025")).strip(),
        "source_publisher": str(raw["source_publisher"]).strip(),
        "source_url": str(raw["source_url"]).strip(),
        "institution_website_url": str(raw.get("institution_website_url", "")).strip() or None,
        "aicte_portal_url": str(raw.get("aicte_portal_url", "https://facilities.aicte-india.org/dashboard/pages/angulardashboard.php#!/approved")).strip(),
        "aishe_portal_url": str(raw.get("aishe_portal_url", "https://dashboard.aishe.gov.in/hedirectory/")).strip() or None,
        "retrieval_date": str(raw.get("retrieval_date", "2026-10-23")).strip(),
        "dataset_version": str(raw.get("dataset_version", "AY-2024-2025-V1")).strip(),
        "validation_status": "VALIDATED",
    }
    normalized["content_checksum"] = compute_record_checksum(normalized)
    return normalized, None


def import_verified_dataset(
    db: Session,
    source_file: Optional[Path | str] = None,
    raw_records: Optional[List[Dict[str, Any]]] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Import and validate public reference institution records with deduplication and dry-run support."""
    # 1. Load records
    if raw_records is None:
        file_path = Path(source_file) if source_file else DEFAULT_DATASET_PATH
        if not file_path.exists():
            return {
                "status": "FAILED",
                "dry_run": dry_run,
                "message": f"Source dataset file not found: {file_path}",
                "records_discovered": 0,
                "records_accepted": 0,
                "records_updated": 0,
                "records_skipped": 0,
                "records_rejected": 0,
                "rejection_reasons": [],
                "batch_checksum": "",
                "import_batch_id": "",
            }
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if not isinstance(loaded, list):
                return {
                    "status": "FAILED",
                    "dry_run": dry_run,
                    "message": "Source dataset must be a JSON array of institution objects",
                    "records_discovered": 0,
                    "records_accepted": 0,
                    "records_updated": 0,
                    "records_skipped": 0,
                    "records_rejected": 0,
                    "rejection_reasons": [],
                    "batch_checksum": "",
                    "import_batch_id": "",
                }
            records_to_process = loaded
        except Exception as exc:
            return {
                "status": "FAILED",
                "dry_run": dry_run,
                "message": f"Failed to parse source dataset JSON: {exc}",
                "records_discovered": 0,
                "records_accepted": 0,
                "records_updated": 0,
                "records_skipped": 0,
                "records_rejected": 0,
                "rejection_reasons": [],
                "batch_checksum": "",
                "import_batch_id": "",
            }
    else:
        records_to_process = raw_records

    import_batch_id = f"batch-{uuid.uuid4().hex[:8]}-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    records_discovered = len(records_to_process)
    records_accepted = 0
    records_updated = 0
    records_skipped = 0
    records_rejected = 0
    rejection_reasons: List[Dict[str, str]] = []

    valid_records: List[Dict[str, Any]] = []
    seen_in_batch: set[str] = set()

    for idx, raw in enumerate(records_to_process):
        norm, error = validate_and_normalize_record(raw)
        if error or norm is None:
            records_rejected += 1
            rejection_reasons.append({
                "index": str(idx),
                "record_preview": str(raw.get("institution_name", "UNKNOWN")),
                "reason": error or "Validation failed",
            })
            continue

        aid = norm["aicte_permanent_id"]
        if aid in seen_in_batch:
            records_rejected += 1
            rejection_reasons.append({
                "index": str(idx),
                "record_preview": norm["institution_name"],
                "reason": f"Duplicate AICTE Permanent ID '{aid}' within the import batch",
            })
            continue

        seen_in_batch.add(aid)
        norm["import_batch_id"] = import_batch_id
        valid_records.append(norm)

    batch_checksum = compute_batch_checksum(valid_records) if valid_records else ""

    # 2. Database deduplication and upsert logic
    for norm in valid_records:
        existing = (
            db.query(PublicReferenceInstitution)
            .filter(PublicReferenceInstitution.aicte_permanent_id == norm["aicte_permanent_id"])
            .first()
        )

        if existing:
            needs_update = (
                existing.content_checksum != norm["content_checksum"]
                or getattr(existing, "source_url", None) != norm.get("source_url")
                or getattr(existing, "institution_website_url", None) != norm.get("institution_website_url")
                or getattr(existing, "aicte_portal_url", None) != norm.get("aicte_portal_url")
                or getattr(existing, "aishe_portal_url", None) != norm.get("aishe_portal_url")
            )
            if not needs_update:
                records_skipped += 1
            else:
                # Fields changed, update if not dry_run
                records_updated += 1
                if not dry_run:
                    for k, v in norm.items():
                        setattr(existing, k, v)
        else:
            records_accepted += 1
            if not dry_run:
                new_inst = PublicReferenceInstitution(**norm)
                db.add(new_inst)

    if not dry_run:
        try:
            db.commit()
            status_text = "SUCCESS"
            msg = f"Successfully imported {records_accepted} new and updated {records_updated} reference institutions."
        except Exception as exc:
            db.rollback()
            logger.error("Database commit failed during dataset import: %s", exc)
            return {
                "status": "FAILED",
                "dry_run": False,
                "message": f"Database commit failed: {exc}",
                "records_discovered": records_discovered,
                "records_accepted": 0,
                "records_updated": 0,
                "records_skipped": 0,
                "records_rejected": records_rejected,
                "rejection_reasons": rejection_reasons,
                "batch_checksum": batch_checksum,
                "import_batch_id": import_batch_id,
            }
    else:
        status_text = "DRY_RUN_COMPLETED"
        msg = f"Dry run passed: {records_accepted} new, {records_updated} to update, {records_skipped} unchanged, {records_rejected} rejected."

    return {
        "status": status_text,
        "dry_run": dry_run,
        "message": msg,
        "records_discovered": records_discovered,
        "records_accepted": records_accepted,
        "records_updated": records_updated,
        "records_skipped": records_skipped,
        "records_rejected": records_rejected,
        "rejection_reasons": rejection_reasons,
        "batch_checksum": batch_checksum,
        "import_batch_id": import_batch_id,
    }


def main():
    parser = argparse.ArgumentParser(description="Import verified public reference technical institutions.")
    parser.add_argument("--file", type=str, default=None, help="Path to JSON dataset file")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing to database")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        summary = import_verified_dataset(db, source_file=args.file, dry_run=args.dry_run)
        print(json.dumps(summary, indent=2))
        if summary["status"] == "FAILED":
            sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
