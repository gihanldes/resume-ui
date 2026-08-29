"""Orchestrates a full resume review: parse once, run every rule, score."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from app.services.extraction import ExtractedDocument
from app.services.parsing import (
    assign_sections,
    extract_bullets,
    extract_contact,
    extract_date_ranges,
    find_gaps,
)
from app.services.rules.ats import check_ats
from app.services.rules.base import Category, Finding, ReviewContext, Rule, Severity
from app.services.rules.contact import check_contact
from app.services.rules.formatting import check_formatting
from app.services.rules.impact import check_impact
from app.services.rules.keywords import build_keyword_report, check_keywords
from app.services.rules.structure import check_structure
from app.services.rules.base import CATEGORY_WEIGHTS
from app.services.scoring import ScoreResult, priority_fixes, score_findings, sort_findings
from app.services.sectioning import split_sections

logger = logging.getLogger(__name__)

ENGINE_VERSION = "1.2"

RULES: tuple[Rule, ...] = (
    check_contact,
    check_structure,
    check_impact,
    check_ats,
    check_formatting,
    check_keywords,
)


@dataclass
class ReviewResult:
    score: ScoreResult
    findings: list[Finding]
    priorities: list[Finding]
    keyword_report: dict[str, Any] | None
    snapshot: dict[str, Any]
    duration_ms: int
    engine_version: str = ENGINE_VERSION
    rule_errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "engine_version": self.engine_version,
            "duration_ms": self.duration_ms,
            "score": self.score.as_dict(),
            "findings": [f.as_dict() for f in self.findings],
            "priorities": [f.as_dict() for f in self.priorities],
            "keyword_report": self.keyword_report,
            "snapshot": self.snapshot,
            "rule_errors": self.rule_errors,
        }


# Findings that always belong to one section, keyed by id.
_SECTION_BY_ID: dict[str, str] = {
    "structure.education_before_experience": "education",
    "structure.summary_not_first": "summary",
    "structure.experience_thin": "experience",
    "structure.skills_bloated": "skills",
    "structure.skills_obsolete": "skills",
    "ats.no_parsable_dates": "experience",
    "formatting.date_format_mixed": "experience",
    "formatting.multiple_current": "experience",
    "formatting.employment_gaps": "experience",
    "keywords.no_skills_section": "skills",
}


def _locate_evidence(ctx: ReviewContext, phrases: list[str]) -> str | None:
    """Dominant canonical section whose text contains the quoted evidence."""
    import re
    from collections import Counter

    counts: Counter[str] = Counter()
    flattened = [
        (s.name, re.sub(r"\s+", " ", s.text.lower()))
        for s in ctx.sections
        if s.name != "unknown" and s.text
    ]
    for phrase in phrases:
        needle = re.sub(r"\s+", " ", phrase.lower()).strip()
        if len(needle) < 4:
            continue
        for name, text in flattened:
            if needle in text:
                counts[name] += 1
                break
    if not counts:
        return None
    return counts.most_common(1)[0][0]


def attribute_section(finding: Finding, ctx: ReviewContext) -> str | None:
    """Which resume section a finding is about; None = the whole document.

    Grouping the report by the resume's own sections is how people revise, so
    every finding that can honestly be pinned to one section is.
    """
    if finding.section is not None:
        return finding.section
    if finding.id in _SECTION_BY_ID:
        return _SECTION_BY_ID[finding.id]
    if finding.id.startswith("contact."):
        return "header"
    if finding.id.startswith(("structure.missing_", "structure.empty_")):
        return finding.id.rsplit("_", 1)[-1]
    if finding.id == "structure.low_value_sections" and finding.evidence:
        return finding.evidence[0]
    if finding.id.startswith("impact."):
        located = _locate_evidence(ctx, finding.evidence)
        if located:
            return located
        # Bullet-level findings without usable evidence: the judged bullets'
        # dominant section is the honest home.
        from collections import Counter

        bullet_sections = Counter(b.section for b in ctx.experience_bullets)
        if bullet_sections:
            top, _ = bullet_sections.most_common(1)[0]
            if top not in ("unknown", "header"):
                return top
        return "experience" if ctx.has_section("experience") else None
    return None


def build_context(
    document: ExtractedDocument,
    *,
    target_role: str | None = None,
    job_description: str | None = None,
    today: date | None = None,
) -> ReviewContext:
    today = today or datetime.now(timezone.utc).date()
    text = document.text
    sections = split_sections(text)
    date_ranges = assign_sections(extract_date_ranges(text), sections)
    work_ranges = [r for r in date_ranges if r.section in ("experience", "projects")]
    return ReviewContext(
        text=text,
        sections=sections,
        contact=extract_contact(text, sections),
        bullets=extract_bullets(sections),
        date_ranges=date_ranges,
        gaps=find_gaps(work_ranges or date_ranges, today),
        document=document,
        today=today,
        target_role=target_role,
        job_description=job_description,
    )


def _snapshot(ctx: ReviewContext) -> dict[str, Any]:
    """What the parser understood — shown to the user so results are auditable."""
    months = ctx.experience_months
    return {
        "contact": ctx.contact.as_dict(),
        "sections": [
            {
                "name": s.name,
                "heading": s.heading,
                "word_count": s.word_count,
            }
            for s in ctx.sections
            if s.name != "unknown" or s.word_count
        ],
        "detected_sections": sorted(ctx.section_names),
        "bullet_count": len(ctx.bullets),
        "date_ranges": [r.as_dict() for r in ctx.date_ranges],
        "gaps": [g.as_dict() for g in ctx.gaps],
        "experience_months": months,
        "experience_years": round(months / 12, 1),
        "word_count": ctx.document.word_count,
        "page_count": ctx.document.page_count,
        "extraction": ctx.document.meta(),
    }


def enrich_priorities(priorities: list[Finding], overall: float) -> tuple[list[dict], float]:
    """Priorities with their overall-scale point gain, plus a projected score.

    A finding's penalty is on its category's 100-point scale; the gain a user
    sees must be on the overall scale, so it is weighted the same way the
    score is. The projection assumes the listed fixes land.
    """
    enriched: list[dict] = []
    total_gain = 0.0
    for finding in priorities:
        gain = round(finding.penalty * CATEGORY_WEIGHTS[finding.category] / 100.0, 1)
        total_gain += gain
        enriched.append({**finding.as_dict(), "overall_gain": gain})
    projected = round(min(100.0, overall + total_gain), 1)
    return enriched, projected


def review(
    document: ExtractedDocument,
    *,
    target_role: str | None = None,
    job_description: str | None = None,
    today: date | None = None,
) -> ReviewResult:
    """Run the full deterministic review."""
    started = time.perf_counter()
    ctx = build_context(
        document, target_role=target_role, job_description=job_description, today=today
    )

    findings: list[Finding] = []
    rule_errors: list[str] = []
    for rule in RULES:
        try:
            findings.extend(rule(ctx))
        except Exception:  # one broken rule must not fail the whole review
            logger.exception("Rule %s failed", getattr(rule, "__name__", rule))
            rule_errors.append(getattr(rule, "__name__", "unknown_rule"))

    for finding in findings:
        finding.section = attribute_section(finding, ctx)

    applicable = set(Category)
    if not ctx.has_job_description:
        applicable.discard(Category.KEYWORDS)

    score = score_findings(findings, applicable=applicable)
    ordered = sort_findings(findings)

    try:
        keyword_report = build_keyword_report(ctx)
    except Exception:
        logger.exception("Keyword report failed")
        keyword_report = None

    return ReviewResult(
        score=score,
        findings=ordered,
        priorities=priority_fixes(ordered),
        keyword_report=keyword_report,
        snapshot=_snapshot(ctx),
        duration_ms=int((time.perf_counter() - started) * 1000),
        rule_errors=rule_errors,
    )
