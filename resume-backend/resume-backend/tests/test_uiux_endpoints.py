"""Tests for the rename and logout-others endpoints added by the UX overhaul."""

from __future__ import annotations

import asyncio
import uuid

import httpx

from app.db import init_db
from app.main import app

_initialised = False


async def _client() -> httpx.AsyncClient:
    global _initialised
    if not _initialised:
        await init_db()
        _initialised = True
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def _register(client: httpx.AsyncClient) -> dict:
    email = f"ux-{uuid.uuid4().hex[:10]}@example.com"
    response = await client.post(
        "/api/auth/register",
        json={"email": email, "password": "Str0ngPassw0rd!x"},
    )
    assert response.status_code == 201, response.text
    return {"email": email, **response.json()}


def _auth(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _upload(client: httpx.AsyncClient, tokens: dict) -> dict:
    content = b"""John Doe
john@example.com
(555) 123-4567

PROFESSIONAL SUMMARY
Senior backend engineer with 8+ years of experience building scalable systems. Expertise in Python, Go, and distributed systems. Proven track record of leading technical projects and mentoring engineers.

EXPERIENCE
Senior Backend Engineer | TechCorp Inc | 2020-Present
- Led a team of 4 engineers in designing and implementing a microservices architecture handling 10M+ requests daily
- Architected a distributed task queue system using Kafka and Redis, reducing latency by 40%
- Improved system reliability from 99.5% to 99.99% uptime through comprehensive monitoring and incident response
- Mentored 3 junior engineers, resulting in 2 promotions

Backend Engineer | StartupXYZ | 2018-2020
- Built RESTful APIs serving 100K+ users in Python/FastAPI
- Implemented caching strategies using Redis that reduced database load by 60%
- Developed automated deployment pipelines using Terraform and Docker

SKILLS
Languages: Python, Go, JavaScript, SQL
Frameworks: FastAPI, Django, SQLAlchemy
Databases: PostgreSQL, MongoDB, Redis
Infrastructure: Kubernetes, Docker, Terraform, AWS

EDUCATION
B.S. Computer Science | State University | 2015"""
    response = await client.post(
        "/api/resumes",
        headers=_auth(tokens),
        files={"file": ("mine.txt", content, "text/plain")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_rename_updates_filename():
    async def flow():
        async with await _client() as client:
            tokens = await _register(client)
            resume = await _upload(client, tokens)

            # Verify fresh resume has no analyses
            response = await client.patch(
                f"/api/resumes/{resume['id']}",
                headers=_auth(tokens),
                json={"filename": "  Backend resume v2  "},
            )
            assert response.status_code == 200, response.text
            renamed = response.json()
            assert renamed["filename"] == "Backend resume v2"
            assert renamed["analysis_count"] == 0, "Fresh resume should have no analyses"

            # Run an analysis to verify decoration is live
            analysis_response = await client.post(
                f"/api/resumes/{resume['id']}/analyze",
                headers=_auth(tokens),
                json={"include_ai": False},
            )
            assert analysis_response.status_code == 201, analysis_response.text

            # Rename again and verify analysis_count is updated
            response2 = await client.patch(
                f"/api/resumes/{resume['id']}",
                headers=_auth(tokens),
                json={"filename": "Backend resume v3"},
            )
            assert response2.status_code == 200, response2.text
            renamed2 = response2.json()
            assert renamed2["filename"] == "Backend resume v3"
            assert renamed2["analysis_count"] == 1, "Should reflect the analysis we just ran"

            # Verify GET returns same analysis_count
            detail = await client.get(f"/api/resumes/{resume['id']}", headers=_auth(tokens))
            assert detail.json()["filename"] == "Backend resume v3"
            assert detail.json()["analysis_count"] == renamed2["analysis_count"], \
                "Rename response and GET should agree on analysis_count"

    asyncio.run(flow())


def test_rename_rejects_blank_and_foreign():
    async def flow():
        async with await _client() as client:
            owner = await _register(client)
            stranger = await _register(client)
            resume = await _upload(client, owner)

            blank = await client.patch(
                f"/api/resumes/{resume['id']}", headers=_auth(owner), json={"filename": "   "}
            )
            assert blank.status_code == 422

            foreign = await client.patch(
                f"/api/resumes/{resume['id']}",
                headers=_auth(stranger),
                json={"filename": "hijack"},
            )
            assert foreign.status_code == 404

            anonymous = await client.patch(
                f"/api/resumes/{resume['id']}", json={"filename": "nope"}
            )
            assert anonymous.status_code == 401

    asyncio.run(flow())


def test_logout_others_keeps_current_session():
    async def flow():
        async with await _client() as client:
            first = await _register(client)
            # A second sign-in creates a second session for the same user.
            second = (
                await client.post(
                    "/api/auth/login",
                    json={"email": first["email"], "password": "Str0ngPassw0rd!x"},
                )
            ).json()

            response = await client.post(
                "/api/auth/logout-others",
                headers=_auth(second),
                json={"refresh_token": second["refresh_token"]},
            )
            assert response.status_code == 200, response.text
            assert "1 other session" in response.json()["detail"]

            # The current session still refreshes.
            alive = await client.post(
                "/api/auth/refresh", json={"refresh_token": second["refresh_token"]}
            )
            assert alive.status_code == 200

            # The first session's refresh token is now revoked.
            dead = await client.post(
                "/api/auth/refresh", json={"refresh_token": first["refresh_token"]}
            )
            assert dead.status_code == 401

    asyncio.run(flow())


def test_logout_others_rejects_unrecognised_refresh_token():
    async def flow():
        async with await _client() as client:
            user = await _register(client)
            other = await _register(client)
            # Presenting someone else's refresh token must not be accepted.
            response = await client.post(
                "/api/auth/logout-others",
                headers=_auth(user),
                json={"refresh_token": other["refresh_token"]},
            )
            assert response.status_code == 400

    asyncio.run(flow())
