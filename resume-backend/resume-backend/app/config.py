"""Application settings, loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- app ---
    app_name: str = "Resume Reviewer API"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api"
    # When set (the Docker image sets it), the built frontend is served from
    # this directory and the API and app share one origin.
    static_dir: str | None = None

    # --- security ---
    # Override in production. A random dev key is generated if left unset.
    secret_key: str = Field(default="")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 14
    # argon2 tuning (defaults are the argon2-cffi recommendations)
    argon2_time_cost: int = 3
    argon2_memory_cost: int = 65536
    argon2_parallelism: int = 4

    # --- database ---
    database_url: str = "sqlite+aiosqlite:///./resume_reviewer.db"
    db_echo: bool = False

    # --- CORS ---
    # NoDecode stops pydantic-settings from JSON-parsing the .env value, so a
    # plain comma-separated CORS_ORIGINS reaches the validator below intact.
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # --- uploads ---
    max_upload_bytes: int = 5 * 1024 * 1024  # 5 MB
    allowed_extensions: set[str] = {".pdf", ".docx", ".txt", ".md"}
    max_resumes_per_user: int = 50

    # --- rate limiting (in-memory, per process) ---
    rate_limit_enabled: bool = True
    rate_limit_window_seconds: int = 60
    rate_limit_auth_per_window: int = 10
    rate_limit_upload_per_window: int = 15
    rate_limit_analyze_per_window: int = 6
    # Reject request bodies larger than this before reading them.
    max_request_bytes: int = 12 * 1024 * 1024

    # --- OpenAI ---
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    openai_timeout_seconds: float = 90.0
    openai_max_output_tokens: int = 4000
    # Hard cap on resume text sent to the model, to bound cost.
    ai_max_input_chars: int = 24_000
    ai_enabled: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        """Allow CORS_ORIGINS to be a comma-separated string in .env."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @property
    def ai_available(self) -> bool:
        return bool(self.ai_enabled and self.openai_api_key)

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.secret_key:
        if settings.environment == "production":
            raise RuntimeError(
                "SECRET_KEY must be set when ENVIRONMENT=production. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(48))'"
            )
        # Dev convenience: ephemeral key. Tokens are invalidated on restart.
        import secrets

        settings.secret_key = secrets.token_urlsafe(48)
    elif len(settings.secret_key.encode()) < 32 and settings.environment == "production":
        # HS256 keys shorter than the hash output weaken the signature (RFC 7518 §3.2).
        raise RuntimeError(
            "SECRET_KEY must be at least 32 bytes. "
            "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(48))'"
        )
    return settings


settings = get_settings()
