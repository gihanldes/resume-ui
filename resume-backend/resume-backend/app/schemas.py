"""Pydantic request/response models for the HTTP API."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
_PASSWORD_MIN = 10


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=_PASSWORD_MIN, max_length=128)
    full_name: str | None = Field(default=None, max_length=160)
    target_role: str | None = Field(default=None, max_length=160)

    @field_validator("password")
    @classmethod
    def _strong_enough(cls, value: str) -> str:
        checks = (
            (re.search(r"[a-z]", value), "a lowercase letter"),
            (re.search(r"[A-Z]", value), "an uppercase letter"),
            (re.search(r"\d", value), "a digit"),
        )
        missing = [label for ok, label in checks if not ok]
        if missing:
            raise ValueError(f"Password must contain {', '.join(missing)}.")
        return value

    @field_validator("full_name", "target_role")
    @classmethod
    def _tidy(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access-token lifetime in seconds.")


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str | None
    target_role: str | None
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=160)
    target_role: str | None = Field(default=None, max_length=160)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=_PASSWORD_MIN, max_length=128)

    _strong_enough = field_validator("new_password")(UserRegister._strong_enough.__func__)  # type: ignore[attr-defined]


class AccountDelete(BaseModel):
    password: str = Field(min_length=1, max_length=128)


# --------------------------------------------------------------------------- #
# Resumes
# --------------------------------------------------------------------------- #
class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    content_type: str
    file_size: int
    page_count: int
    word_count: int
    created_at: datetime
    analysis_count: int = 0
    latest_score: float | None = None


class ResumeRename(BaseModel):
    filename: str = Field(min_length=1, max_length=255)

    @field_validator("filename")
    @classmethod
    def _strip_filename(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Filename cannot be empty.")
        return value


class ResumeDetail(ResumeOut):
    raw_text: str
    extraction_meta: dict[str, Any]


# --------------------------------------------------------------------------- #
# Analyses
# --------------------------------------------------------------------------- #
class AnalyzeRequest(BaseModel):
    target_role: str | None = Field(default=None, max_length=160)
    job_description: str | None = Field(default=None, max_length=20_000)
    include_ai: bool = Field(
        default=True,
        description="Run the AI review layer. Ignored when the server has no API key.",
    )

    @field_validator("target_role", "job_description")
    @classmethod
    def _tidy(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


class AnalysisSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    resume_id: str
    status: str
    overall_score: float
    target_role: str | None
    created_at: datetime
    has_ai_review: bool = False
    resume_filename: str | None = None


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    resume_id: str
    status: str
    error: str | None
    target_role: str | None
    job_description: str | None
    overall_score: float
    category_scores: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    keyword_report: dict[str, Any] | None
    parsed_snapshot: dict[str, Any]
    ai_review: dict[str, Any] | None
    ai_model: str | None
    ai_error: str | None
    engine_version: str
    duration_ms: int
    created_at: datetime
    resume_filename: str | None = None
    band: str | None = None
    verdict: str | None = None
    priorities: list[dict[str, Any]] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Misc
# --------------------------------------------------------------------------- #
class HealthOut(BaseModel):
    status: str
    environment: str
    ai_available: bool
    ai_model: str | None
    engine_version: str


class MessageOut(BaseModel):
    detail: str
