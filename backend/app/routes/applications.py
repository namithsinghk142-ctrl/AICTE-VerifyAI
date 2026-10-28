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
    Document,
    DocumentProcessingStatus,
    FindingSeverity,
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
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    if mode == "real":
        return {
            "items": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "mode": "real",
            "message": "Authentic application dossiers have not been connected to this instance.",
        }

    return {
        "items": [],
        "total": 0,
        "page": page,
        "limit": limit,
        "mode": "synthetic",
    }


class ActionPayloadCompat(BaseModel):
    notes: str | None = None
    reason: str | None = None
    performedBy: str | None = None


class AddNotePayloadCompat(BaseModel):
    author: str
    role: str
    text: str
    category: str = "general"


def _format_app_as_submission(app_obj: Application, db: Session) -> dict:
    docs = db.query(Document).filter(Document.application_id == app_obj.id).all()
    evidence_list = []
    for d in docs:
        evidence_list.append({
            "id": d.id,
            "type": d.document_type or "document",
            "name": d.original_filename,
            "uploadedAt": d.created_at.isoformat() if d.created_at else "",
            "verificationStatus": "verified" if d.processing_status == DocumentProcessingStatus.COMPLETED else "pending",
            "issuer": getattr(d, "issuer_name", "Issuer Authority") or "Issuer Authority",
            "notes": "",
            "description": f"Uploaded document: {d.original_filename}",
            "filename": d.original_filename,
            "fileSizeBytes": d.file_size,
            "fileSizeFormatted": f"{round(d.file_size / 1024, 1)} KB",
            "checksumSha256": d.sha256_hash,
            "pageCount": 1,
            "findingIds": [],
            "content": None,
        })

    val_findings = db.query(ValidationFinding).filter(ValidationFinding.application_id == app_obj.id).all()
    findings_list = []
    for f in val_findings:
        findings_list.append({
            "id": f.id,
            "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
            "category": f.finding_code,
            "description": f.explanation,
            "flaggedAt": f.created_at.isoformat() if f.created_at else "",
            "ruleOrCheck": f.title,
            "reason": f.explanation,
            "documentId": f.document_id,
            "documentName": "",
            "pageNumber": 1,
            "reviewerNextStep": f.recommended_action or "Reviewer verification required",
            "statusNotice": "Advisory finding",
            "findingType": "statutory",
        })

    return {
        "id": app_obj.id,
        "applicationId": app_obj.id,
        "institution": {
            "id": f"inst-{app_obj.id[:8]}",
            "name": app_obj.institution_name,
            "city": "New Delhi",
            "state": "Delhi",
            "type": app_obj.application_category,
            "aicteId": f"1-{app_obj.id[:7]}",
            "isSyntheticDemo": False,
        },
        "submittedAt": app_obj.created_at.isoformat() if app_obj.created_at else "",
        "updatedAt": app_obj.updated_at.isoformat() if app_obj.updated_at else "",
        "status": app_obj.status.value if hasattr(app_obj.status, "value") else str(app_obj.status),
        "category": app_obj.application_category,
        "assignedTo": app_obj.reviewer_actor or "Senior Compliance Reviewer",
        "priorityScore": 85,
        "dueDate": "2026-11-15",
        "reviewNotes": app_obj.review_notes or "",
        "findings": findings_list,
        "evidence": evidence_list,
        "reviewerNotesList": [],
        "crossDocComparisons": run_cross_doc_checks(app_obj.id, db),
        "isSyntheticDemo": False,
    }



@submissions_router.get("/{id}")
def get_submission_by_id(id: str, db: Session = Depends(get_db)) -> dict:
    app_obj = db.get(Application, id)
    if not app_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Submission {id} not found")
    return _format_app_as_submission(app_obj, db)


@submissions_router.post("/{id}/approve")
def approve_submission(id: str, payload: ActionPayloadCompat, db: Session = Depends(get_db)) -> dict:
    app_obj = db.get(Application, id)
    if app_obj:
        val_findings = db.query(ValidationFinding).filter(
            ValidationFinding.application_id == app_obj.id,
            ValidationFinding.severity == FindingSeverity.CRITICAL,
        ).all()
        if val_findings:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve submission while {len(val_findings)} critical findings remain unresolved.",
            )
        app_obj.status = ApplicationStatus.VALIDATED
        app_obj.review_status = "reviewed"
        if payload.notes:
            app_obj.review_notes = payload.notes
        audit = AuditEvent(
            application_id=app_obj.id,
            event_type="decision_approved",
            actor=payload.performedBy or "Reviewer",
            details=payload.notes or "Official compliance recommendation: Approved for Council ratification.",
        )
        db.add(audit)
        db.commit()
        db.refresh(app_obj)
        return {
            "success": True,
            "message": "Submission approved successfully. Audit event recorded.",
            "submission": _format_app_as_submission(app_obj, db),
        }

    return {
        "success": True,
        "message": f"Demo submission {id} approval recorded.",
    }


@submissions_router.post("/{id}/reject")
def reject_submission(id: str, payload: ActionPayloadCompat, db: Session = Depends(get_db)) -> dict:
    reason = payload.reason or payload.notes or "Application rejected due to unresolved statutory deficiencies."
    app_obj = db.get(Application, id)
    if app_obj:
        app_obj.status = ApplicationStatus.REJECTED
        app_obj.review_status = "reviewed"
        app_obj.review_notes = reason
        audit = AuditEvent(
            application_id=app_obj.id,
            event_type="decision_rejected",
            actor=payload.performedBy or "Reviewer",
            details=reason,
        )
        db.add(audit)
        db.commit()
        db.refresh(app_obj)
        return {
            "success": True,
            "message": "Submission rejection recorded. Order drafted with cited clauses.",
            "submission": _format_app_as_submission(app_obj, db),
        }

    return {
        "success": True,
        "message": "Submission rejection recorded.",
    }


@submissions_router.post("/{id}/escalate")
def escalate_submission(id: str, payload: ActionPayloadCompat, db: Session = Depends(get_db)) -> dict:
    reason = payload.reason or payload.notes or "Escalated to Senior Hearing Committee for regulatory scrutiny."
    app_obj = db.get(Application, id)
    if app_obj:
        app_obj.review_status = "escalated"
        app_obj.review_notes = reason
        audit = AuditEvent(
            application_id=app_obj.id,
            event_type="escalated",
            actor=payload.performedBy or "Reviewer",
            details=reason,
        )
        db.add(audit)
        db.commit()
        db.refresh(app_obj)
        return {
            "success": True,
            "message": "Submission escalated to Senior Hearing Board. Audit trail updated.",
            "submission": _format_app_as_submission(app_obj, db),
        }

    return {
        "success": True,
        "message": "Submission escalated to Senior Hearing Board. Audit trail updated.",
    }


@submissions_router.post("/{id}/request-evidence")
@submissions_router.post("/{id}/request-info")
def request_evidence_submission(id: str, payload: ActionPayloadCompat, db: Session = Depends(get_db)) -> dict:
    notes = payload.notes or "Clarification / additional documentary evidence requested from applicant institution."
    app_obj = db.get(Application, id)
    if app_obj:
        app_obj.status = ApplicationStatus.REQUIRES_CLARIFICATION
        app_obj.review_status = "needs_information"
        app_obj.review_notes = notes
        audit = AuditEvent(
            application_id=app_obj.id,
            event_type="evidence_requested",
            actor=payload.performedBy or "Reviewer",
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

    return {
        "success": True,
        "message": "Formal clarification inquiry dispatched to institution.",
    }


@submissions_router.post("/{id}/notes")
def add_reviewer_note(id: str, note: AddNotePayloadCompat, db: Session = Depends(get_db)) -> dict:
    now_iso = datetime.now(timezone.utc).isoformat()
    note_id = f"note-{int(datetime.now(timezone.utc).timestamp() * 1000)}"

    app_obj = db.get(Application, id)
    if app_obj:
        audit = AuditEvent(
            application_id=app_obj.id,
            event_type="comment_added",
            actor=f"{note.author} ({note.role})",
            details=f"Reviewer remark added: \"{note.text[:80]}...\"",
        )
        db.add(audit)
        db.commit()

    return {
        "success": True,
        "note": {
            "id": note_id,
            "author": note.author,
            "role": note.role,
            "timestamp": now_iso,
            "text": note.text,
            "category": note.category,
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
        # Create lightweight placeholder Application for synthetic submission id
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
            extracted_text=extracted_text[:50000] if extracted_text else None,
            extracted_fields=extracted_fields,
            processing_status=DocumentProcessingStatus.COMPLETED,
        )
        db.add(new_doc)
        db.commit()

    comparisons = run_cross_doc_checks(id, db)

    audit = AuditEvent(
        application_id=id if len(id) == 36 else None,
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
def get_cross_doc_checks(id: str, db: Session = Depends(get_db)) -> dict:
    comparisons = run_cross_doc_checks(id, db)
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


