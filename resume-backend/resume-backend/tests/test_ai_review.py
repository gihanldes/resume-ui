"""Tests for the OpenAI review layer, with the network call stubbed out."""

from __future__ import annotations

import asyncio
from datetime import date
from types import SimpleNamespace

import pytest

from app.config import settings
from app.services import ai_review as ai
from app.services.analyzer import review
from app.services.extraction import extract_document

TODAY = date(2026, 8, 28)

RESUME = """\
JANE DOE
jane@example.com | (415) 555-0142 | linkedin.com/in/janedoe | Berlin, Germany

SUMMARY
Backend engineer, six years in payments.

EXPERIENCE
Engineer, Acme | Jan 2020 - Present
• Responsible for the billing service
• Cut invoice errors by 22%

EDUCATION
BSc Computer Science, TU Berlin | 2013 - 2017

SKILLS
Python, PostgreSQL, Kubernetes
"""


def _result():
    return review(extract_document("r.txt", RESUME.encode()), today=TODAY)


def test_prompt_labels_untrusted_input_and_bounds_length(monkeypatch):
    monkeypatch.setattr(settings, "ai_max_input_chars", 200)
    prompt = ai.build_prompt(
        "X" * 5000, _result(), target_role="Backend Engineer", job_description="Need Python."
    )
    assert "BEGIN RESUME (untrusted data)" in prompt
    assert "END RESUME" in prompt
    assert "BEGIN JOB DESCRIPTION (untrusted data)" in prompt
    assert "truncated for length" in prompt
    # The resume body must actually be cut, not just annotated.
    assert prompt.count("X") <= 260


def test_system_instructions_forbid_invented_metrics_and_injection():
    text = ai.SYSTEM_INSTRUCTIONS.lower()
    assert "never invent" in text
    assert "untrusted" in text
    assert "ignore previous instructions" in text
    assert "placeholder" in text


def test_no_api_key_degrades_without_raising(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", None)
    outcome = asyncio.run(ai.generate_ai_review(RESUME, _result()))
    assert outcome.ok is False
    assert outcome.review is None
    assert "OPENAI_API_KEY" in (outcome.error or "")


def test_disabled_flag_short_circuits(monkeypatch):
    monkeypatch.setattr(settings, "ai_enabled", False)
    outcome = asyncio.run(ai.generate_ai_review(RESUME, _result()))
    assert outcome.ok is False
    assert "disabled" in (outcome.error or "").lower()


class _FakeResponses:
    def __init__(self, parsed=None, raise_exc=None):
        self._parsed = parsed
        self._raise = raise_exc
        self.calls: list[dict] = []

    async def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self._raise:
            raise self._raise
        return SimpleNamespace(output_parsed=self._parsed)


class _FakeClient:
    def __init__(self, parsed=None, raise_exc=None):
        self.responses = _FakeResponses(parsed, raise_exc)
        self.closed = False

    async def close(self):
        self.closed = True


def _install(monkeypatch, client):
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "ai_enabled", True)
    import openai

    monkeypatch.setattr(openai, "AsyncOpenAI", lambda **kwargs: client)
    return client


def _sample_review() -> ai.AIReview:
    return ai.AIReview(
        overall_impression="Reads as a competent mid-level engineer.",
        estimated_level="mid-level backend engineer",
        strengths=["Quantified the invoice-error reduction."],
        weaknesses=["The billing bullet describes a duty, not a result."],
        priority_actions=[
            ai.PriorityAction(title="Quantify the billing bullet", why="No outcome.", how="Add [X%].")
        ],
        bullet_rewrites=[
            ai.BulletRewrite(
                original="Responsible for the billing service",
                improved="Owned the billing service, cutting failed charges by [X%]",
                rationale="Leads on ownership and leaves the metric explicit.",
            )
        ],
        tailoring_notes=[],
        red_flags=[],
    )


def test_successful_review_is_returned_as_a_dict(monkeypatch):
    client = _install(monkeypatch, _FakeClient(parsed=_sample_review()))
    outcome = asyncio.run(
        ai.generate_ai_review(RESUME, _result(), target_role="Backend Engineer")
    )
    assert outcome.ok
    assert outcome.review is not None
    assert outcome.review["estimated_level"] == "mid-level backend engineer"
    assert outcome.review["bullet_rewrites"][0]["improved"].startswith("Owned")
    assert outcome.error is None
    assert client.closed is True

    call = client.responses.calls[0]
    assert call["text_format"] is ai.AIReview
    assert call["model"] == settings.openai_model
    assert call["instructions"] == ai.SYSTEM_INSTRUCTIONS


def test_missing_parsed_output_is_reported_not_raised(monkeypatch):
    _install(monkeypatch, _FakeClient(parsed=None))
    outcome = asyncio.run(ai.generate_ai_review(RESUME, _result()))
    assert outcome.ok is False
    assert outcome.error


@pytest.mark.parametrize(
    "exc,expected",
    [
        (RuntimeError("Incorrect API key provided: authentication failed"), "OPENAI_API_KEY"),
        (TimeoutError("request timeout"), "timed out"),
    ],
)
def test_api_failures_degrade_with_a_useful_message(monkeypatch, exc, expected):
    client = _install(monkeypatch, _FakeClient(raise_exc=exc))
    outcome = asyncio.run(ai.generate_ai_review(RESUME, _result()))
    assert outcome.ok is False
    assert expected.lower() in (outcome.error or "").lower()
    # The client must still be closed on the failure path.
    assert client.closed is True
