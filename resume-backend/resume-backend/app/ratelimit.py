"""Small in-memory rate limiter.

Sliding-window counters keyed by IP (unauthenticated routes) or user id
(authenticated ones). In-memory is correct for a single-process deployment;
run multiple workers and this must move to Redis — noted in the README.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Annotated, Awaitable, Callable

from fastapi import Depends, HTTPException, Request, status

from app.config import settings
from app.deps import get_current_user
from app.models import User

_buckets: dict[str, deque[float]] = {}


def reset() -> None:
    """Clear all counters. Test hook."""
    _buckets.clear()


def _hit(key: str, limit: int) -> None:
    if not settings.rate_limit_enabled:
        return
    window = settings.rate_limit_window_seconds
    now = time.monotonic()
    bucket = _buckets.setdefault(key, deque())
    while bucket and now - bucket[0] > window:
        bucket.popleft()
    if len(bucket) >= limit:
        retry_after = max(1, int(window - (now - bucket[0])) + 1)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Try again shortly.",
            headers={"Retry-After": str(retry_after)},
        )
    bucket.append(now)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def by_ip(scope: str, setting_name: str) -> Callable[..., Awaitable[None]]:
    async def dependency(request: Request) -> None:
        _hit(f"{scope}:{_client_ip(request)}", getattr(settings, setting_name))

    return dependency


def by_user(scope: str, setting_name: str) -> Callable[..., Awaitable[None]]:
    async def dependency(user: Annotated[User, Depends(get_current_user)]) -> None:
        _hit(f"{scope}:{user.id}", getattr(settings, setting_name))

    return dependency


# Shared limiter instances, one per route class.
auth_ip_limit = by_ip("auth", "rate_limit_auth_per_window")
upload_user_limit = by_user("upload", "rate_limit_upload_per_window")
analyze_user_limit = by_user("analyze", "rate_limit_analyze_per_window")
