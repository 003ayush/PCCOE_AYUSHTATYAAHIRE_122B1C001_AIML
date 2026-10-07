"""SQLite persistence via SQLAlchemy.

Mirrors the Pydantic schemas and adds the audit log. ``init_db()`` is
idempotent; call it on startup. Sessions come from ``session_scope()``.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from sqlalchemy import create_engine, JSON, DateTime, Integer, String, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class _ReviewColumns:
    """Approval-status columns shared by every reviewable row."""

    status: Mapped[str] = mapped_column(String, default="pending")
    reviewer: Mapped[str | None] = mapped_column(String, nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AssetRow(_ReviewColumns, Base):
    """Persisted asset suggestion."""

    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    security_properties_required: Mapped[list] = mapped_column(JSON, default=list)
    source_ids: Mapped[list] = mapped_column(JSON, default=list)


class ThreatRow(_ReviewColumns, Base):
    """Persisted threat scenario with impact/feasibility details as JSON."""

    __tablename__ = "threats"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    stride_category: Mapped[str] = mapped_column(String)
    affected_assets: Mapped[list] = mapped_column(JSON, default=list)
    source_ids: Mapped[list] = mapped_column(JSON, default=list)
    impact: Mapped[dict] = mapped_column(JSON, default=dict)
    feasibility: Mapped[dict] = mapped_column(JSON, default=dict)


class RiskRow(_ReviewColumns, Base):
    """Persisted risk rating for a threat."""

    __tablename__ = "risks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    threat_id: Mapped[str] = mapped_column(String, index=True)
    impact_value: Mapped[int] = mapped_column(Integer, default=0)
    feasibility_value: Mapped[int] = mapped_column(Integer, default=0)
    risk_value: Mapped[int] = mapped_column(Integer, default=0)
    rationale: Mapped[str] = mapped_column(Text, default="")
    needs_expert_review: Mapped[bool] = mapped_column(Boolean, default=False)


class MitigationRow(_ReviewColumns, Base):
    """Persisted mitigation linked to a threat."""

    __tablename__ = "mitigations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    threat_id: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(Text)
    cybersecurity_requirement: Mapped[str] = mapped_column(Text)
    source_ids: Mapped[list] = mapped_column(JSON, default=list)


class VerificationRow(_ReviewColumns, Base):
    """Persisted verification link from a mitigation to a test activity."""

    __tablename__ = "verifications"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    mitigation_id: Mapped[str] = mapped_column(String, index=True)
    test_method: Mapped[str] = mapped_column(Text)
    status_detail: Mapped[str] = mapped_column(String, default="planned")
    note: Mapped[str] = mapped_column(Text, default="")


class AuditLogRow(Base):
    """Append-only audit trail of every review decision."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_type: Mapped[str] = mapped_column(String)
    item_id: Mapped[str] = mapped_column(String, index=True)
    action: Mapped[str] = mapped_column(String)
    reviewer: Mapped[str] = mapped_column(String)
    note: Mapped[str] = mapped_column(Text, default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


# Engine/session factory bound to the configured SQLite URL.
engine = create_engine(settings.sqlite_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    """Create all tables if they do not exist yet."""
    Base.metadata.create_all(engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional session scope (commit on success, rollback on error)."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
