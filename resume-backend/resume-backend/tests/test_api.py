"""API-level tests for the hardening layer: headers, body cap, rate limiting."""

from __future__ import annotations

import asyncio

import httpx

from app import ratelimit
from app.config import settings
from app.db import init_db
from app.main import app

_initialised = False


async def _client() -> httpx.AsyncClient:
    global _initialised
    if not _initialised:
        await init_db()
        _initialised = True
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    )


def test_security_headers_and_request_id():
    async def flow():
        async with await _client() as client:
            response = await client.get("/api/health")
            assert response.status_code == 200
            assert response.headers["x-content-type-options"] == "nosniff"
            assert response.headers["x-frame-options"] == "DENY"
            assert response.headers["referrer-policy"] == "no-referrer"
            assert response.headers["cache-control"] == "no-store"
            assert response.headers.get("x-request-id")

    asyncio.run(flow())


def test_client_request_id_is_echoed():
    async def flow():
        async with await _client() as client:
            response = await client.get("/api/health", headers={"X-Request-ID": "trace-me-123"})
            assert response.headers["x-request-id"] == "trace-me-123"

    asyncio.run(flow())


def test_oversized_body_is_rejected_before_parsing():
    async def flow():
        async with await _client() as client:
            body = b"x" * (settings.max_request_bytes + 16)
            response = await client.post(
                "/api/auth/login",
                content=body,
                headers={"Content-Type": "application/json"},
            )
            assert response.status_code == 413
            assert "too large" in response.json()["detail"].lower()

    asyncio.run(flow())


def test_login_attempts_are_rate_limited(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_auth_per_window", 3)
    ratelimit.reset()

    async def flow():
        async with await _client() as client:
            payload = {"email": "nobody@example.com", "password": "wrong"}
            for _ in range(3):
                response = await client.post("/api/auth/login", json=payload)
                assert response.status_code == 401  # counted, but under the limit
            response = await client.post("/api/auth/login", json=payload)
            assert response.status_code == 429
            assert "retry-after" in response.headers
            assert int(response.headers["retry-after"]) >= 1

    try:
        asyncio.run(flow())
    finally:
        ratelimit.reset()


def test_rate_limit_window_slides(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_auth_per_window", 2)
    monkeypatch.setattr(settings, "rate_limit_window_seconds", 0)  # instant expiry
    ratelimit.reset()

    async def flow():
        async with await _client() as client:
            payload = {"email": "nobody@example.com", "password": "wrong"}
            for _ in range(4):
                response = await client.post("/api/auth/login", json=payload)
                assert response.status_code == 401  # window expires each call

    try:
        asyncio.run(flow())
    finally:
        ratelimit.reset()
