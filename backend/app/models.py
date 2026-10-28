"""SQLAlchemy ORM models for VerifyAI."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    """Return the current UTC timestamp (timezone-aware)."""
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    """Generate a new UUID4 string for use as a primary key."""
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ApplicationStatus(str, enum.Enum):
    """Lifecycle statuses for an AICTE application."""

    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    VALIDATED = "validated"
    REJECTED = "rejected"
    REQUIRES_CLARIFICATION = "requires_clarification"


class ReviewStatus(str, enum.Enum):
    """Reviewer workflow statuses for an application."""

    PENDING = "pending"
    IN_REVIEW = "in_review"
    NEEDS_INFORMATION = "needs_information"
    REVIEWED = "reviewed"
    ESCALATED = "escalated"


class DocumentProcessingStatus(str, enum.Enum):
    """Processing pipeline statuses for an uploaded document."""

    UPLOADED = "uploaded"
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class FindingSeverity(str, enum.Enum):
    """Severity levels for validation findings."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingReviewStatus(str, enum.Enum):
    """Human-review statuses for a validation finding."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    ESCALATED = "escalated"


class DataClassification(str, enum.Enum):
    """Classification of data provenance in AICTE VerifyAI."""

    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"
    PUBLIC_REFERENCE = "PUBLIC_REFERENCE"
    AUTHENTIC_APPLICATION = "AUTHENTIC_APPLICATION"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class Application(Base):
    """An AICTE approval / compliance application submitted by an institution."""

    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    institution_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    application_category: Mapped[str] = mapped_column(String(100), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(9), nullable=False)  # e.g. "2025-2026"
    status: Mapped[ApplicationStatus] = mapped_column(
        SAEnum(ApplicationStatus), default=ApplicationStatus.SUBMITTED, nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    data_classification: Mapped[str] = mapped_column(
        String(50), default=DataClassification.SYNTHETIC_DEMO.value, nullable=False
    )
    is_synthetic_demo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    source_record_id: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    import_batch_id: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)

    application_number: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    institution_city: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    institution_state: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    institution_type: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)
    aicte_id: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    priority_score: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    due_date: Mapped[str | None] = mapped_column(String(30), nullable=True, default=None)

    review_status: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    reviewer_actor: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)

    # Relationships
    documents: Mapped[list["Document"]] = relationship(back_populates="application", cascade="all, delete-orphan")
    findings: Mapped[list["ValidationFinding"]] = relationship(back_populates="application", cascade="all, delete-orphan")
    audit_events: Mapped[list["AuditEvent"]] = relationship(back_populates="application", cascade="all, delete-orphan")
    compliance_evaluations: Mapped[list["ComplianceEvaluation"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    issuer_verifications: Mapped[list["IssuerVerification"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    review_actions: Mapped[list["ReviewAction"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    reviewer_notes: Mapped[list["ReviewerNote"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )


class Document(Base):
    """A document attached to an application for AI-powered verification."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)  # Kept for Phase 1 compatibility
    document_type: Mapped[str] = mapped_column(String(100), nullable=False, default="unclassified")
    storage_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    processing_status: Mapped[DocumentProcessingStatus] = mapped_column(
        SAEnum(DocumentProcessingStatus), default=DocumentProcessingStatus.UPLOADED, nullable=False,
    )
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_json: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    page_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    issuer_name: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    application: Mapped["Application"] = relationship(back_populates="documents")
    findings: Mapped[list["ValidationFinding"]] = relationship(back_populates="document")
    issuer_verifications: Mapped[list["IssuerVerification"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class ValidationFinding(Base):
    """A finding produced by the AI validation engine (or a human reviewer)."""

    __tablename__ = "validation_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    document_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True,
    )
    finding_code: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[FindingSeverity] = mapped_column(SAEnum(FindingSeverity), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[FindingReviewStatus] = mapped_column(
        SAEnum(FindingReviewStatus), default=FindingReviewStatus.PENDING, nullable=False,
    )
    highlight_snippet_id: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    page_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    finding_type: Mapped[str | None] = mapped_column(String(50), nullable=True, default=None)
    status_notice: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    rule_citation: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    document_name: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    application: Mapped["Application"] = relationship(back_populates="findings")
    document: Mapped["Document | None"] = relationship(back_populates="findings")


class AuditEvent(Base):
    """Immutable audit trail entry for an application."""

    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    actor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)
    metadata_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    application: Mapped["Application"] = relationship(back_populates="audit_events")


class IssuerVerification(Base):
    """Result of comparing document issuer data against a verification provider."""

    __tablename__ = "issuer_verifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    issuer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issuer_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    certificate_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(50), nullable=False)
    is_mock: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_officially_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    matched_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    unmatched_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_human_review: Mapped[bool] = mapped_column(default=True, nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    document: Mapped["Document"] = relationship(back_populates="issuer_verifications")
    application: Mapped["Application"] = relationship(back_populates="issuer_verifications")


class ReviewAction(Base):
    """Immutable record of a reviewer decision or action on an application."""

    __tablename__ = "review_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    previous_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False, default="demo_reviewer")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    application: Mapped["Application"] = relationship(back_populates="review_actions")


class ComplianceEvaluation(Base):
    """Result of evaluating an application against a regulatory compliance rule."""

    __tablename__ = "compliance_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    rule_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    requirement_title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(9), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    source_designation: Mapped[str] = mapped_column(String(50), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_considered: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    missing_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_human_review: Mapped[bool] = mapped_column(default=False, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    application: Mapped["Application"] = relationship(back_populates="compliance_evaluations")


class Reviewer(Base):
    """Stores reviewer credentials and profile for authentication."""

    __tablename__ = "reviewers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=False, default="Senior Compliance Reviewer")
    avatar_initials: Mapped[str] = mapped_column(String(10), nullable=False, default="RO")
    assigned_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    resolved_this_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auth_provider: Mapped[str] = mapped_column(String(50), default="local", nullable=False)
    google_sub: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    registration_status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


ReviewerModel = Reviewer


class AccountAllowlist(Base):
    """Administrator-controlled allowlist of emails approved for system access."""

    __tablename__ = "account_allowlist"

    email: Mapped[str] = mapped_column(String(255), primary_key=True)  # Normalized lowercase
    assigned_role: Mapped[str] = mapped_column(String(100), default="Senior Compliance Reviewer", nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)


AllowedEmail = AccountAllowlist


class PublicReferenceInstitution(Base):
    """Verified technical institution record from official public registry (e.g. AICTE / AISHE).

    Contains strictly factual directory data. No synthetic findings, risk scores,
    or invented discrepancies are ever attached.
    """

    __tablename__ = "public_reference_institutions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    aicte_permanent_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    institution_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    city_or_district: Mapped[str] = mapped_column(String(100), nullable=False)
    institution_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aishe_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    sponsoring_body: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approval_status: Mapped[str] = mapped_column(String(100), default="Approved (Public Reference)", nullable=False)
    academic_year: Mapped[str] = mapped_column(String(20), default="2024–2025", nullable=False)
    source_publisher: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    institution_website_url: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    aicte_portal_url: Mapped[str] = mapped_column(
        String(500),
        default="https://facilities.aicte-india.org/dashboard/pages/angulardashboard.php#!/approved",
        nullable=False,
    )
    aishe_portal_url: Mapped[str | None] = mapped_column(
        String(500),
        default="https://dashboard.aishe.gov.in/hedirectory/",
        nullable=True,
    )
    retrieval_date: Mapped[str] = mapped_column(String(30), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(50), default="AY-2024-2025-V1", nullable=False)
    import_batch_id: Mapped[str] = mapped_column(String(100), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(50), default="VALIDATED", nullable=False)
    content_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


class CrossDocComparison(Base):
    """Stores cross-document reconciliation and consistency check results."""

    __tablename__ = "cross_doc_comparisons"

    id: Mapped[str] = mapped_column(String(100), primary_key=True, default=_new_uuid)
    submission_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    has_discrepancy: Mapped[bool] = mapped_column(Boolean, default=False)
    status_text: Mapped[str] = mapped_column(String(255), nullable=False)
    entries_json: Mapped[str] = mapped_column(Text, nullable=False)
    human_review_recommendation: Mapped[str] = mapped_column(Text, nullable=False)


CrossDocComparisonModel = CrossDocComparison




class ReviewerNote(Base):
    """An internal note or remark left by a compliance reviewer on an application."""

    __tablename__ = "reviewer_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    application_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="general", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relationships
    application: Mapped["Application"] = relationship(back_populates="reviewer_notes")
