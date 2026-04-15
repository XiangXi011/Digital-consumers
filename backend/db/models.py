"""SQLAlchemy ORM models — 7 tables for market research platform.

Tables:
    users          — JWT auth users (admin / editor / viewer)
    projects       — replaces JSON session files in outputs/dingtalk_sessions/
    reports        — replaces file-scan report discovery
    share_tokens   — replaces report_shares.json
    audit_log      — new: user action audit trail
    system_settings — replaces .env key-value parsing
    frozen_snapshots — replaces file-based snapshot storage
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


# ─── 1. users ────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    email = Column(String(320), unique=True, nullable=False)
    display_name = Column(String(120), nullable=False)
    role = Column(
        Enum("admin", "editor", "viewer", name="user_role"),
        nullable=False,
        default="viewer",
    )
    password_hash = Column(String(256), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    projects = relationship("Project", back_populates="owner")
    reports = relationship("Report", back_populates="owner")

    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_role", "role"),
    )


# ─── 2. projects ─────────────────────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    owner_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)

    # Legacy DingTalk identifiers (keep for backward compat)
    session_id = Column(String(256), unique=True, nullable=False, index=True)
    group_id = Column(String(256), nullable=False, default="")
    conversation_id = Column(String(256), nullable=False, default="")
    user_id = Column(String(256), nullable=False, default="")

    name = Column(String(256), nullable=False, default="")
    status = Column(String(64), nullable=False, default="collecting")
    project_type = Column(String(64), nullable=False, default="concept_test")

    # Structured input fields — same schema as TaskSession.fields
    fields = Column(JSONB, nullable=False, default=dict)
    # TaskSession custom lists
    attachments = Column(JSONB, nullable=False, default=list)
    source_links = Column(JSONB, nullable=False, default=list)
    custom_questions = Column(JSONB, nullable=False, default=list)
    product_context_notes = Column(JSONB, nullable=False, default=list)
    follow_up_context = Column(Text, nullable=False, default="")

    # Generated artefacts
    business_brief = Column(JSONB, nullable=True)
    research_plan = Column(JSONB, nullable=True)
    readiness_decision = Column(JSONB, nullable=True)
    html_report_path = Column(Text, nullable=True)
    json_report_path = Column(Text, nullable=True)
    metrics_path = Column(Text, nullable=True)

    # Flags
    checklist_sent = Column(Boolean, nullable=False, default=False)
    partial_run_authorized = Column(Boolean, nullable=False, default=False)
    authorization_requested_at = Column(DateTime(timezone=True), nullable=True)
    authorization_requested_by = Column(String(256), nullable=True)

    # Snapshot refs
    live_snapshot_refs = Column(JSONB, nullable=False, default=list)
    frozen_snapshot_refs = Column(JSONB, nullable=False, default=list)
    retention_policy = Column(JSONB, nullable=False, default=dict)
    suspended_messages = Column(JSONB, nullable=False, default=list)

    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    owner = relationship("User", back_populates="projects")
    reports = relationship("Report", back_populates="project")
    snapshots = relationship("FrozenSnapshot", back_populates="project")

    __table_args__ = (
        Index("ix_projects_owner_id", "owner_id"),
        Index("ix_projects_status", "status"),
        Index("ix_projects_created_at", "created_at"),
        Index("ix_projects_session_id", "session_id"),
    )


# ─── 3. reports ──────────────────────────────────────────────────────────────

class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    owner_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)

    report_type = Column(String(64), nullable=False, default="full")
    name = Column(String(256), nullable=False, default="")
    json_path = Column(Text, nullable=True)
    html_path = Column(Text, nullable=True)
    meta = Column(JSONB, nullable=True)
    evaluation_metrics = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    owner = relationship("User", back_populates="reports")
    project = relationship("Project", back_populates="reports")

    __table_args__ = (
        Index("ix_reports_owner_id", "owner_id"),
        Index("ix_reports_created_at", "created_at"),
        Index("ix_reports_project_id", "project_id"),
    )


# ─── 4. share_tokens ─────────────────────────────────────────────────────────

class ShareToken(Base):
    __tablename__ = "share_tokens"

    token = Column(String(128), primary_key=True)
    report_id = Column(UUID(as_uuid=False), ForeignKey("reports.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, nullable=False, default=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        Index("ix_share_tokens_report_id", "report_id"),
    )


# ─── 5. audit_log ────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    action = Column(String(64), nullable=False)
    resource = Column(String(64), nullable=False)
    resource_id = Column(String(256), nullable=True)
    detail = Column(JSONB, nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        Index("ix_audit_log_user_id", "user_id"),
        Index("ix_audit_log_action", "action"),
        Index("ix_audit_log_created_at", "created_at"),
    )


# ─── 6. system_settings ──────────────────────────────────────────────────────

class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(128), primary_key=True)
    value = Column(Text, nullable=True)
    is_secret = Column(Boolean, nullable=False, default=False)
    updated_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)


# ─── 7. frozen_snapshots ─────────────────────────────────────────────────────

class FrozenSnapshot(Base):
    __tablename__ = "frozen_snapshots"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    stage = Column(String(64), nullable=False, default="")
    payload = Column(JSONB, nullable=False, default=dict)
    version_bundle = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    project = relationship("Project", back_populates="snapshots")

    __table_args__ = (
        Index("ix_frozen_snapshots_project_id", "project_id"),
    )


# ─── 8. personas ────────────────────────────────────────────────────────────

class Persona(Base):
    __tablename__ = "personas"

    id = Column(String(64), primary_key=True)  # e.g. "M01", "custom_abc"
    name = Column(String(200), nullable=False, default="")
    budget_band = Column(String(32), nullable=False, default="")
    veto_trigger = Column(Text, nullable=False, default="")
    decision_weights = Column(JSONB, nullable=False, default=dict)
    veto_rules = Column(JSONB, nullable=False, default=list)
    feature_scoring_rubric = Column(JSONB, nullable=False, default=dict)
    tags = Column(JSONB, nullable=False, default=list)
    is_custom = Column(Boolean, nullable=False, default=False)
    created_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("ix_personas_is_custom", "is_custom"),
    )
