"""SQLAlchemy ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base

# Use JSONB on Postgres, plain JSON elsewhere (SQLite).
JSONType = JSON().with_variant(JSONB(), "postgresql")


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
        server_default=func.now(),
        nullable=False,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(160))
    target_role: Mapped[str | None] = mapped_column(String(160))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    resumes: Mapped[list["Resume"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    analyses: Mapped[list["Analysis"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class RefreshToken(Base):
    """Server-side record of an issued refresh token, so it can be rotated/revoked."""

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # SHA-256 of the token; the raw token is never stored.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

    @property
    def is_active(self) -> bool:
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return self.revoked_at is None and expires > _utcnow()


class Resume(Base, TimestampMixin):
    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    # SHA-256 of the extracted text, used to detect re-uploads of the same resume.
    text_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Layout signals captured at extraction time (columns, tables, images...).
    extraction_meta: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)

    user: Mapped["User"] = relationship(back_populates="resumes")
    analyses: Mapped[list["Analysis"]] = relationship(
        back_populates="resume",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Analysis.created_at.desc()",
    )

    __table_args__ = (Index("ix_resumes_user_created", "user_id", "created_at"),)


class Analysis(Base, TimestampMixin):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    error: Mapped[str | None] = mapped_column(Text)

    target_role: Mapped[str | None] = mapped_column(String(160))
    job_description: Mapped[str | None] = mapped_column(Text)

    overall_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    category_scores: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONType, default=list, nullable=False
    )
    findings: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, default=list, nullable=False)
    keyword_report: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    parsed_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict, nullable=False)

    ai_review: Mapped[dict[str, Any] | None] = mapped_column(JSONType)
    ai_model: Mapped[str | None] = mapped_column(String(80))
    ai_error: Mapped[str | None] = mapped_column(Text)

    engine_version: Mapped[str] = mapped_column(String(20), default="1.0", nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    resume: Mapped["Resume"] = relationship(back_populates="analyses")
    user: Mapped["User"] = relationship(back_populates="analyses")

    __table_args__ = (Index("ix_analyses_user_created", "user_id", "created_at"),)
