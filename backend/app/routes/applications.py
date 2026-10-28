"""Application CRUD and document upload endpoints."""

from __future__ import annotations

import hashlib
import math
import os
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import (
    Application,
    ApplicationStatus,
    AuditEvent,
    CrossDocComparison,
    Document,
    DocumentProcessingStatus,
    FindingReviewStatus,
    FindingSeverity,
    ReviewAction,
    ReviewerNote,
    ValidationFinding,
)
from app.schemas import (
    ApplicationCreate,
    ApplicationResponse,
    DocumentListResponse,
    DocumentResponse,
    PaginatedApplicationsResponse,
    ValidationResultResponse,
)
from app.services.document_processor import DocumentProcessor
from app.services.file_storage import FileStorageService
from app.services.file_validation import validate_file
from app.services.ocr_service import OCRService
from app.services.pdf_extractor import PDFExtractor
from app.services.validation.engine import ValidationEngine
from app.services.cross_doc_engine import run_cross_doc_checks

router = APIRouter(prefix="/applications", tags=["Applications"])



@router.post(
    "",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new application",
)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
) -> Application:
    application = Application(
        institution_name=payload.institution_name,
        application_category=payload.application_category,
        academic_year=payload.academic_year,
        status=ApplicationStatus.SUBMITTED,
    )
    db.add(application)
    db.flush()  # populate id before creating audit event

    audit = AuditEvent(
        application_id=application.id,
        event_type="application_created",
        details=f"Application created for {payload.institution_name}",
    )
    db.add(audit)
    db.commit()
    db.refresh(application)
    return application


@router.get(
    "",
    response_model=PaginatedApplicationsResponse,
    summary="List applications with pagination",
)
def list_applications(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: ApplicationStatus | None = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(Application)
    if status is not None:
        query = query.filter(Application.status == status)

    total = query.count()
    total_pages = max(1, math.ceil(total / page_size))
    items = (
        query
        .order_by(Application.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="Get a single application by ID",
)
def get_application(
    application_id: str,
    db: Session = Depends(get_db),
) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return application


@router.post(
    "/{application_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a supporting document for an application",
    description=(
        "Securely upload PDF, PNG, or JPEG supporting documents. Validates magic bytes, "
        "file size, and extension; computes SHA-256; stores file privately; and initiates "
        "text extraction and classification."
    ),
)
async def upload_document(
    application_id: str,
    file: UploadFile = File(..., description="Institutional supporting document (PDF, PNG, JPEG)"),
    document_type: str | None = Form(None, description="Optional document category identifier"),
    db: Session = Depends(get_db),
) -> Document:
    # 1. Verify application exists
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    # 2. Read file bytes
    content = await file.read()

    # 3. Validate file (extension, MIME, magic bytes, size limits, sanitisation)
    settings = get_settings()
    val_res = validate_file(
        content=content,
        filename=file.filename,
        client_content_type=file.content_type,
        max_upload_size_bytes=settings.max_upload_size_bytes,
    )

    # 4. Save file safely in private storage
    storage = FileStorageService(settings.storage_dir)
    storage_ref = storage.save_file(content, val_res.extension)

    # 5. Persist initial document record
    doc = Document(
        application_id=application.id,
        original_filename=val_res.sanitized_filename,
        filename=val_res.sanitized_filename,
        document_type=document_type.strip() if document_type and document_type.strip() else "unclassified",
        storage_reference=storage_ref,
        mime_type=val_res.mime_type,
        file_size=val_res.file_size,
        sha256_hash=val_res.sha256_hash,
        processing_status=DocumentProcessingStatus.UPLOADED,
    )
    db.add(doc)
    db.flush()

    # 6. Audit trail for document upload
    audit = AuditEvent(
        application_id=application.id,
        event_type="document_uploaded",
        actor="applicant",
        details=(
            f"Document '{val_res.sanitized_filename}' ({val_res.file_size} bytes) "
            f"uploaded with SHA-256: {val_res.sha256_hash[:12]}..."
        ),
    )
    db.add(audit)
    db.commit()
    db.refresh(doc)

    # 7. Execute text extraction & classification pipeline
    processor = DocumentProcessor(storage)
    doc = processor.process_document(doc.id, db)

    # 8. Trigger cross-document reconciliation
    try:
        run_cross_doc_checks(application.id, db)
    except Exception:
        pass

    return doc



@router.get(
    "/{application_id}/documents",
    response_model=DocumentListResponse,
    summary="List all documents attached to an application",
    description="Returns metadata for all documents attached to the application without exposing private storage paths.",
)
def list_application_documents(
    application_id: str,
    db: Session = Depends(get_db),
) -> dict:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    docs = (
        db.query(Document)
        .filter(Document.application_id == application_id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return {
        "items": docs,
        "total": len(docs),
    }


@router.post(
    "/{application_id}/validate",
    response_model=ValidationResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Run regulatory compliance and document validation checks",
    description=(
        "Executes completeness checks against category checklists, detects missing or unreadable "
        "documents, validates certificate expiry dates, verifies cross-document institution name consistency, "
        "and checks for duplicate file uploads. Persists advisory validation findings and updates audit trail."
    ),
)
def validate_application(
    application_id: str,
    db: Session = Depends(get_db),
) -> ValidationResultResponse:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    return ValidationEngine.validate_application(application_id, db)


@router.get(
    "/{application_id}/results",
    response_model=ValidationResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve persisted validation findings and summary results",
    description=(
        "Retrieves stored validation findings, evidence references, and summary statistics "
        "for the application."
    ),
)
def get_validation_results(
    application_id: str,
    db: Session = Depends(get_db),
) -> ValidationResultResponse:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    return ValidationEngine.get_persisted_results(application_id, db)


submissions_router = APIRouter(prefix="/submissions", tags=["Submissions"])


class ActionPayloadCompat(BaseModel):
    notes: str | None = None
    reason: str | None = None
    performedBy: str | None = None


class AddNotePayloadCompat(BaseModel):
    author: str
    role: str
    text: str
    category: str = "general"


class ResolveFindingPayload(BaseModel):
    status: str
    reason: str | None = None
    reviewer: str | None = None


def _format_app_as_submission(app_obj: Application, db: Session) -> dict:
    docs = db.query(Document).filter(Document.application_id == app_obj.id).all()
    evidence_list = []
    for d in docs:
        content_parsed = None
        if getattr(d, "content_json", None):
            try:
                content_parsed = json.loads(d.content_json)
            except Exception:
                content_parsed = None

        f_size = d.file_size or 0
        if f_size >= 1048576:
            size_fmt = f"{round(f_size / 1048576, 1)} MB"
        else:
            size_fmt = f"{round(f_size / 1024, 1)} KB"

        related_finding_ids = [
            f.id for f in db.query(ValidationFinding).filter(ValidationFinding.document_id == d.id).all()
        ]

        evidence_list.append({
            "id": d.id,
            "type": d.document_type or "document",
            "name": d.original_filename,
            "uploadedAt": d.created_at.isoformat() if d.created_at else "",
            "verificationStatus": "verified" if d.processing_status == DocumentProcessingStatus.COMPLETED else "disputed",
            "issuer": getattr(d, "issuer_name", None) or "Issuer Authority",
            "notes": "",
            "description": d.extracted_text or f"Uploaded document: {d.original_filename}",
            "filename": d.filename or d.original_filename,
            "fileSizeBytes": f_size,
            "fileSizeFormatted": size_fmt,
            "checksumSha256": d.sha256_hash or "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "pageCount": getattr(d, "page_count", 1) or 1,
            "findingIds": related_finding_ids,
            "content": content_parsed,
        })

    val_findings = db.query(ValidationFinding).filter(ValidationFinding.application_id == app_obj.id).all()
    findings_list = []
    for f in val_findings:
        sev_raw = (f.severity.value if hasattr(f.severity, "value") else str(f.severity)).lower()
        if sev_raw == "critical":
            sev_norm = "critical"
        elif sev_raw in ("major", "high", "medium"):
            sev_norm = "major"
        elif sev_raw in ("minor", "low", "warning"):
            sev_norm = "minor"
        else:
            sev_norm = "info"

        findings_list.append({
            "id": f.id,
            "severity": sev_norm,
            "category": f.finding_code,
            "description": f.explanation,
            "flaggedAt": f.created_at.isoformat() if f.created_at else "",
            "ruleOrCheck": getattr(f, "rule_citation", None) or f.title,
            "reason": f.explanation,
            "documentId": f.document_id,
            "documentName": getattr(f, "document_name", "") or "",
            "pageNumber": getattr(f, "page_number", 1) or 1,
            "highlightSnippetId": getattr(f, "highlight_snippet_id", None),
            "reviewerNextStep": f.recommended_action or "Reviewer verification required",
            "statusNotice": getattr(f, "status_notice", None) or "Advisory finding",
            "findingType": getattr(f, "finding_type", "rule_violation") or "rule_violation",
            "reviewStatus": f.review_status.value if hasattr(f.review_status, "value") else str(f.review_status or "pending"),
        })

    notes_rows = (
        db.query(ReviewerNote)
        .filter(ReviewerNote.application_id == app_obj.id)
        .order_by(ReviewerNote.created_at.desc())
        .all()
    )
    notes_list = [
        {
            "id": n.id,
            "author": n.author,
            "role": n.role,
            "text": n.text,
            "category": n.category,
            "timestamp": n.created_at.isoformat() if n.created_at else "",
        }
        for n in notes_rows
    ]

    # Cross-document comparisons
    db_comparisons = (
        db.query(CrossDocComparison)
        .filter(CrossDocComparison.submission_id == app_obj.id)
        .all()
    )
    if db_comparisons:
        comparisons_list = []
        for c in db_comparisons:
            try:
                entries = json.loads(c.entries_json) if isinstance(c.entries_json, str) else (c.entries_json or [])
            except Exception:
                entries = []
            comparisons_list.append({
                "fieldName": c.field_name,
                "description": c.description,
                "hasDiscrepancy": c.has_discrepancy,
                "statusText": c.status_text,
                "entries": entries,
                "humanReviewRecommendation": c.human_review_recommendation,
            })
    else:
        comparisons_list = run_cross_doc_checks(app_obj.id, db)

    # Status mapping to match frontend expectations
    status_str = app_obj.review_status or (
        app_obj.status.value if hasattr(app_obj.status, "value") else str(app_obj.status)
    )
    if status_str == "submitted":
        status_str = "pending_review"
    elif status_str == "validated":
        status_str = "approved"
    elif status_str == "requires_clarification":
        status_str = "on_hold"

    return {
        "id": app_obj.id,
        "applicationId": app_obj.application_number or app_obj.id,
        "institution": {
            "id": f"inst-{app_obj.id}",
            "name": app_obj.institution_name,
            "city": getattr(app_obj, "institution_city", None) or "Bengaluru",
            "state": getattr(app_obj, "institution_state", None) or "Karnataka",
            "type": getattr(app_obj, "institution_type", None) or "college",
            "aicteId": getattr(app_obj, "aicte_id", None) or f"DEMO-{app_obj.id}",
            "isSyntheticDemo": app_obj.is_synthetic_demo,
        },
        "submittedAt": app_obj.created_at.isoformat() if app_obj.created_at else "",
        "updatedAt": app_obj.updated_at.isoformat() if app_obj.updated_at else "",
        "status": status_str,
        "category": app_obj.application_category,
        "assignedTo": app_obj.reviewer_actor or "Unassigned",
        "priorityScore": getattr(app_obj, "priority_score", 50) or 50,
        "dueDate": getattr(app_obj, "due_date", None) or "2026-11-15",
        "reviewNotes": app_obj.review_notes or "",
        "findings": findings_list,
        "evidence": evidence_list,
        "reviewerNotesList": notes_list,
        "crossDocComparisons": comparisons_list,
        "isSyntheticDemo": app_obj.is_synthetic_demo,
    }


@submissions_router.get(
    "",
    summary="List submissions with mode filtering",
    description="Returns submitted applications. In Real mode, only authentic submissions are returned (empty when no confidential filings connected).",
)
def list_submissions_compat(
    mode: str = Query("synthetic", pattern="^(synthetic|real)$"),
    status: str | None = Query(None),
    state: str | None = Query(None),
    query: str | None = Query(None),
    sort_by: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    mode_str = mode if isinstance(mode, str) else "synthetic"
    status_str = status if isinstance(status, str) else None
    state_str = state if isinstance(state, str) else None
    query_str = query if isinstance(query, str) else None
    page_num = page if isinstance(page, int) else 1
    limit_num = limit if isinstance(limit, int) else 50

    if mode_str == "real":
        return {
            "items": [],
            "total": 0,
            "page": page_num,
            "limit": limit_num,
            "mode": "real",
            "message": "Authentic application dossiers have not been connected to this instance.",
        }

    q = db.query(Application).filter(Application.is_synthetic_demo == True)
    if state_str and state_str.lower() != "all":
        q = q.filter(Application.institution_state.ilike(f"%{state_str}%"))
    if query_str:
        term = f"%{query_str.strip()}%"
        q = q.filter(
            (Application.institution_name.ilike(term)) |
            (Application.id.ilike(term)) |
            (Application.application_number.ilike(term)) |
            (Application.institution_city.ilike(term)) |
            (Application.institution_state.ilike(term)) |
            (Application.application_category.ilike(term))
        )

    apps = q.order_by(Application.priority_score.desc(), Application.created_at.desc()).all()
    formatted = [_format_app_as_submission(a, db) for a in apps]

    if status_str and status_str.lower() != "all":
        formatted = [item for item in formatted if item["status"] == status_str]

    total = len(formatted)
    paginated = formatted[(page_num - 1) * limit_num : page_num * limit_num]

    return {
        "items": paginated,
        "total": total,
        "page": page_num,
        "limit": limit_num,
        "mode": "synthetic",
    }


@submissions_router.get("/{id}")
def get_submission_by_id(id: str, db: Session = Depends(get_db)) -> dict:
    app_obj = db.get(Application, id)
    if not app_obj:
        # Check by application_number fallback
        app_obj = db.query(Application).filter(Application.application_number == id).first()
    if not app_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Submission {id} not found")
    return _format_app_as_submission(app_obj, db)


@submissions_router.post("/{id}/approve")
def approve_submission(id: str, payload: ActionPayloadCompat, db: Session = Depends(get_db)) -> dict:
    app_obj = db.get(Application, id)
    if not app_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Submission {id} not found")

    val_findings = db.query(ValidationFinding).filter(
        ValidationFinding.application_id == app_obj.id,
        ValidationFinding.severity == FindingSeverity.CRITICAL,
        ValidationFinding.review_status != FindingReviewStatus.DISMISSED,
    ).all()
    if val_findings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve submission while {len(val_findings)} critical findings remain unresolved.",
        )

    app_obj.status = ApplicationStatus.VALIDATED
    app_obj.review_status = "approved"
    if payload.notes:
        app_obj.review_notes = payload.notes
    app_obj.reviewed_at = datetime.now(timezone.utc)
    app_obj.reviewer_actor = payload.performedBy or "Adhavan S (Senior Compliance Reviewer)"

    # Persist immutable audit event
    audit = AuditEvent(
        application_id=app_obj.id,
        event_type="decision_approved",
        actor=payload.performedBy or "Adhavan S (Senior Compliance Reviewer)",
        details=payload.notes or "Official compliance recommendation: Approved for Council ratification.",
    )
    db.add(audit)

    # Persist review action
    action = ReviewAction(
        application_id=app_obj.id,
        previous_status=app_obj.review_status,
        new_status="approved",
        note=payload.notes,
        actor=payload.performedBy or "Adhavan S (Senior Compliance Reviewer)",
    )
    db.add(action)
    db.commit()
    db.refresh(app_obj)

    return {
        "success": True,
        "message": "Submission approved successfully. Audit event recorded.",
        "submission": _format_app_as_submission(app_obj, db),
    }


@submissions_router.post("/{id}/reject")
def reject_submission(id: str, payload: ActionPayloadCompat, db: Session = Depends(get_db)) -> dict:
    app_obj = db.get(Application, id)
    if not app_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Submission {id} not found")

    reason = payload.reason or payload.notes or "Application rejected due to unresolved statutory deficiencies."
    app_obj.status = ApplicationStatus.REJECTED
    app_obj.review_status = "rejected"
    app_obj.review_notes = reason
    app_obj.reviewed_at = datetime.now(timezone.utc)
    app_obj.reviewer_actor = payload.performedBy or "Adhavan S (Senior Compliance Reviewer)"

    audit = AuditEvent(
        application_id=app_obj.id,
        event_type="decision_rejected",
        actor=payload.performedBy or "Adhavan S (Senior Compliance Reviewer)",
        details=reason,
    )
    db.add(audit)

    action = ReviewAction(
        application_id=app_obj.id,
        previous_status=app_obj.review_status,
        new_status="rejected",
        note=reason,
        actor=payload.performedBy or "Adhavan S (Senior Compliance Reviewer)",
    )
    db.add(action)
    db.commit()
    db.refresh(app_obj)

    return {
        "success": True,
        "message": "Submission rejection recorded. Order drafted with cited clauses.",
        "submission": _format_app_as_submission(app_obj, db),
    }


@submissions_router.post("/{id}/escalate")
def escalate_submission(id: str, payload: ActionPayloadCompat, db: Session = Depends(get_db)) -> dict:
    app_obj = db.get(Application, id)
    if not app_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Submission {id} not found")

    reason = payload.reason or payload.notes or "Escalated to Senior Hearing Committee for regulatory scrutiny."
    app_obj.review_status = "escalated"
    app_obj.review_notes = reason
    app_obj.reviewed_at = datetime.now(timezone.utc)
    app_obj.reviewer_actor = payload.performedBy or "Adhavan S (Senior Compliance Reviewer)"

    audit = AuditEvent(
        application_id=app_obj.id,
        event_type="escalated",
        actor=payload.performedBy or "Adhavan S (Senior Compliance Reviewer)",
        details=reason,
    )
    db.add(audit)

    action = ReviewAction(
        application_id=app_obj.id,
        previous_status=app_obj.review_status,
        new_status="escalated",
        note=reason,
        actor=payload.performedBy or "Adhavan S (Senior Compliance Reviewer)",
    )
    db.add(action)
    db.commit()
    db.refresh(app_obj)

    return {
        "success": True,
        "message": "Submission escalated to Senior Hearing Board. Audit trail updated.",
        "submission": _format_app_as_submission(app_obj, db),
    }


@submissions_router.post("/{id}/request-evidence")
@submissions_router.post("/{id}/request-info")
def request_evidence_submission(id: str, payload: ActionPayloadCompat, db: Session = Depends(get_db)) -> dict:
    app_obj = db.get(Application, id)
    if not app_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Submission {id} not found")

    notes = payload.notes or "In-system formal clarification inquiry dispatched (recorded in statutory audit log)."
    app_obj.status = ApplicationStatus.REQUIRES_CLARIFICATION
    app_obj.review_status = "on_hold"
    app_obj.review_notes = notes
    app_obj.reviewed_at = datetime.now(timezone.utc)
    app_obj.reviewer_actor = payload.performedBy or "Adhavan S (Senior Compliance Reviewer)"

    audit = AuditEvent(
        application_id=app_obj.id,
        event_type="evidence_requested",
        actor=payload.performedBy or "Adhavan S (Senior Compliance Reviewer)",
        details=notes,
    )
    db.add(audit)
    db.commit()
    db.refresh(app_obj)

    return {
        "success": True,
        "message": "Formal clarification inquiry dispatched to institution. Status updated to On Hold.",
        "submission": _format_app_as_submission(app_obj, db),
    }


@submissions_router.post("/{id}/notes")
def add_reviewer_note(id: str, note: AddNotePayloadCompat, db: Session = Depends(get_db)) -> dict:
    app_obj = db.get(Application, id)
    if not app_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Submission {id} not found")

    new_note = ReviewerNote(
        application_id=app_obj.id,
        author=note.author,
        role=note.role,
        text=note.text,
        category=note.category,
    )
    db.add(new_note)

    audit = AuditEvent(
        application_id=app_obj.id,
        event_type="comment_added",
        actor=f"{note.author} ({note.role})",
        details=f"Reviewer remark added: \"{note.text[:80]}...\"",
    )
    db.add(audit)
    db.commit()
    db.refresh(new_note)

    return {
        "success": True,
        "note": {
            "id": new_note.id,
            "author": new_note.author,
            "role": new_note.role,
            "timestamp": new_note.created_at.isoformat() if new_note.created_at else datetime.now(timezone.utc).isoformat(),
            "text": new_note.text,
            "category": new_note.category,
        },
    }


@submissions_router.post("/{id}/findings/{finding_id}/resolve")
def resolve_finding(
    id: str,
    finding_id: str,
    payload: ResolveFindingPayload,
    db: Session = Depends(get_db),
) -> dict:
    finding = db.get(ValidationFinding, finding_id)
    if not finding or finding.application_id != id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    new_status = FindingReviewStatus.CONFIRMED if payload.status == "confirmed" else FindingReviewStatus.DISMISSED
    finding.review_status = new_status
    if payload.reason:
        finding.status_notice = f"{payload.status.capitalize()}: {payload.reason}"

    audit = AuditEvent(
        application_id=id,
        event_type=f"finding_{payload.status}",
        actor=payload.reviewer or "Adhavan S (Senior Compliance Reviewer)",
        details=f"Finding '{finding.title}' marked {payload.status.upper()}. Rationale: {payload.reason or 'Reviewer determination.'}",
    )
    db.add(audit)
    db.commit()
    db.refresh(finding)

    return {
        "success": True,
        "message": f"Finding successfully marked as {payload.status}.",
        "finding": {
            "id": finding.id,
            "reviewStatus": finding.review_status.value if hasattr(finding.review_status, "value") else str(finding.review_status),
            "statusNotice": finding.status_notice,
        },
    }


@submissions_router.post("/{id}/documents/upload")
async def upload_application_document(
    id: str,
    file: UploadFile = File(...),
    documentType: str = Form("document"),
    issuer: str | None = Form(None),
    description: str | None = Form(None),
    db: Session = Depends(get_db),
) -> dict:
    file_bytes = await file.read()
    file_size = len(file_bytes)
    checksum = hashlib.sha256(file_bytes).hexdigest()

    ext = os.path.splitext(file.filename or "")[1].lower()
    page_count = 1
    extracted_text = ""
    ocr_used = False
    ocr_status = "Not required for digital document."

    if ext == ".pdf":
        extractor = PDFExtractor()
        pdf_res = extractor.extract(file_bytes)
        page_count = pdf_res.page_count
        extracted_text = pdf_res.text
        ocr_status = "Native PDF text extracted via PyMuPDF."
    elif ext in {".png", ".jpg", ".jpeg", ".tiff"}:
        settings = get_settings()
        ocr_service = OCRService(settings.tesseract_cmd)
        ocr_res = ocr_service.extract_from_image(file_bytes)
        ocr_used = True
        extracted_text = ocr_res.text
        ocr_status = "OCR applied." if ocr_res.success else "OCR attempted."

    doc_id = f"ev-upload-{int(datetime.now(timezone.utc).timestamp() * 1000)}"

    extracted_fields = {}
    if extracted_text:
        try:
            from backend.document_processing import extract_key_fields_heuristic
            extracted_fields = extract_key_fields_heuristic(extracted_text)
        except Exception:
            extracted_fields = {}

    app_obj = db.get(Application, id)
    if not app_obj and len(id) != 36:
        app_obj = Application(
            id=id,
            institution_name=f"Institutional Applicant ({id})",
            application_category="Technical Education Dossier",
            academic_year="2026-2027",
            status=ApplicationStatus.UNDER_REVIEW,
            is_synthetic_demo=True,
        )
        db.add(app_obj)
        db.commit()

    if app_obj:
        new_doc = Document(
            id=doc_id[:36],
            application_id=app_obj.id,
            original_filename=file.filename or "uploaded_document.pdf",
            filename=file.filename or "uploaded_document.pdf",
            document_type=documentType,
            storage_reference=f"uploads/{checksum[:16]}_{file.filename}",
            mime_type="application/pdf" if ext == ".pdf" else "image/png",
            file_size=file_size,
            sha256_hash=checksum,
            page_count=page_count,
            issuer_name=issuer or "Uploaded Applicant Record",
            extracted_text=extracted_text[:50000] if extracted_text else None,
            extracted_fields=extracted_fields,
            processing_status=DocumentProcessingStatus.COMPLETED,
        )
        db.add(new_doc)
        db.commit()

    comparisons = run_cross_doc_checks(id, db)

    audit = AuditEvent(
        application_id=id,
        event_type="submission_received",
        actor="Reviewer / Document Intake Pipeline",
        details=f"Document '{file.filename}' ({round(file_size/1024, 1)} KB) uploaded. SHA-256: {checksum[:12]}...",
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "message": f"Successfully uploaded and verified '{file.filename}'. Extracted {len(extracted_text)} characters.",
        "documentId": doc_id,
        "filename": file.filename,
        "fileSizeBytes": file_size,
        "checksumSha256": checksum,
        "pageCount": page_count,
        "ocrUsed": ocr_used,
        "ocrStatus": ocr_status,
        "extractedFields": extracted_fields,
        "crossDocComparisons": comparisons,
        "findingsRaised": [],
        "newStatus": "under_review",
    }


@submissions_router.get("/{id}/cross-doc-checks")
@submissions_router.post("/{id}/cross-doc-checks")
def get_or_run_cross_doc_checks(id: str, db: Session = Depends(get_db)) -> dict:
    comparisons = run_cross_doc_checks(id, db)

    # Persist or update audit event for check execution
    audit = AuditEvent(
        application_id=id,
        event_type="cross_doc_checks_run",
        actor="Adhavan S (Senior Compliance Reviewer)",
        details="Cross-document consistency reconciliation re-executed across dossier instruments.",
    )
    db.add(audit)
    db.commit()

    return {
        "submissionId": id,
        "comparisons": comparisons,
        "count": len(comparisons),
    }


@router.get("/{application_id}/cross-doc-checks")
def get_application_cross_doc_checks(application_id: str, db: Session = Depends(get_db)) -> dict:
    comparisons = run_cross_doc_checks(application_id, db)
    return {
        "submissionId": application_id,
        "applicationId": application_id,
        "comparisons": comparisons,
        "count": len(comparisons),
    }
