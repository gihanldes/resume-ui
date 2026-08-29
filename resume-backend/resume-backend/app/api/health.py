"""Liveness and capability reporting."""

from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.schemas import HealthOut
from app.services.analyzer import ENGINE_VERSION

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut, summary="Service health and capabilities")
async def health() -> HealthOut:
    return HealthOut(
        status="ok",
        environment=settings.environment,
        ai_available=settings.ai_available,
        ai_model=settings.openai_model if settings.ai_available else None,
        engine_version=ENGINE_VERSION,
    )
