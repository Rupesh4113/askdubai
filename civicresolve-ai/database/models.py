"""
CivicResolve AI - SQLAlchemy Database Models
Covers users, complaints, documents, evidence_sources, approvals, and case_events.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.orm import relationship
from database.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    preferred_language = Column(String(10), default="en", nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    complaints = relationship("Complaint", back_populates="user", cascade="all, delete-orphan")


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=False)
    merchant = Column(String(255), nullable=True)
    purchase_date = Column(String(50), nullable=True)
    amount = Column(Float, nullable=True)
    currency = Column(String(10), default="AED", nullable=False)
    requested_resolution = Column(String(255), nullable=True)
    jurisdiction = Column(String(255), nullable=True)
    status = Column(String(50), default="draft", nullable=False, index=True)
    submission_reference = Column(String(100), nullable=True, index=True)
    draft_complaint_en = Column(Text, nullable=True)
    draft_complaint_localized = Column(Text, nullable=True)
    resolution_plan = Column(Text, nullable=True)  # JSON-encoded plan
    follow_up_date = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="complaints")
    documents = relationship("Document", back_populates="complaint", cascade="all, delete-orphan")
    evidence_sources = relationship("EvidenceSource", back_populates="complaint", cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="complaint", cascade="all, delete-orphan")
    case_events = relationship("CaseEvent", back_populates="complaint", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_complaint_user_status", "user_id", "status"),
    )


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    complaint_id = Column(String(36), ForeignKey("complaints.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    storage_reference = Column(String(500), nullable=False)
    document_type = Column(String(50), default="invoice_or_receipt", nullable=False)
    extracted_data = Column(Text, nullable=True)  # JSON-encoded extracted attributes
    validation_status = Column(String(50), default="pending", nullable=False)
    confidence_score = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    complaint = relationship("Complaint", back_populates="documents")


class EvidenceSource(Base):
    __tablename__ = "evidence_sources"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    complaint_id = Column(String(36), ForeignKey("complaints.id"), nullable=False, index=True)
    source_title = Column(String(255), nullable=False)
    source_url = Column(String(500), nullable=False)
    source_date = Column(String(50), nullable=True)
    snippet = Column(Text, nullable=True)
    relevance_score = Column(Float, default=1.0, nullable=False)
    retrieved_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    complaint = relationship("Complaint", back_populates="evidence_sources")


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    complaint_id = Column(String(36), ForeignKey("complaints.id"), nullable=False, index=True)
    action_type = Column(String(100), nullable=False)
    approved = Column(Boolean, default=False, nullable=False)
    user_notes = Column(Text, nullable=True)
    action_result = Column(Text, nullable=True)  # JSON-encoded result of execution
    approved_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    complaint = relationship("Complaint", back_populates="approvals")


class CaseEvent(Base):
    __tablename__ = "case_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    complaint_id = Column(String(36), ForeignKey("complaints.id"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    complaint = relationship("Complaint", back_populates="case_events")
