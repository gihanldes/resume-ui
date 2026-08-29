"""Rules covering length, density and internal consistency."""

from __future__ import annotations

import re
from collections.abc import Iterator

from app.services.rules.base import Category, Finding, ReviewContext, Severity

CAT = Category.FORMATTING

# Length expectations scale with career length, not with how much you can write.
def _expected_pages(months_experience: int) -> int:
    if months_experience >= 144:   # 12+ years
        return 3
    if months_experience >= 60:    # 5+ years
        return 2
    return 1


def check_formatting(ctx: ReviewContext) -> Iterator[Finding]:
    doc = ctx.document
    words = doc.word_count
    months = ctx.experience_months
    max_pages = _expected_pages(months)

    # --- page count ---------------------------------------------------------
    if doc.page_count > max_pages:
        years = months // 12
        yield Finding(
            id="formatting.too_long",
            category=CAT, severity=Severity.WARNING,
            title=f"{doc.page_count} pages for roughly {years} years of experience",
            detail=(
                f"At this career stage a resume should fit {max_pages} page"
                f"{'s' if max_pages > 1 else ''}. Beyond that, later pages are rarely "
                "read, so anything important on them is effectively invisible."
            ),
            fix="Cut the oldest roles to one line each and remove anything not relevant to the target job.",
            penalty=min(24.0, 12.0 * (doc.page_count - max_pages)),
        )

    # --- word count ---------------------------------------------------------
    if words < 250:
        yield Finding(
            id="formatting.too_short",
            category=CAT, severity=Severity.CRITICAL,
            title=f"Only {words} words of content",
            detail=(
                "There is not enough substance here for a recruiter to assess you, or "
                "for keyword matching to find anything. A one-page resume still runs "
                "to roughly 350-500 words."
            ),
            fix="Add 3-5 achievement bullets per role, plus a skills section.",
            penalty=30,
        )
    elif words < 350:
        yield Finding(
            id="formatting.thin",
            category=CAT, severity=Severity.WARNING,
            title=f"{words} words is on the thin side",
            detail="Most competitive resumes run 400-800 words. This one is likely under-selling the work.",
            fix="Expand your most recent role with concrete, quantified achievements.",
            penalty=12,
        )
    elif words > 1200:
        yield Finding(
            id="formatting.verbose",
            category=CAT, severity=Severity.WARNING,
            title=f"{words} words is long for a resume",
            detail=(
                "Past roughly 1,000 words the reader is skimming and the density of "
                "signal per line drops. Length is not the same as substance."
            ),
            fix="Cut duty-style bullets and keep only achievements with an outcome.",
            penalty=12,
        )

    # --- date consistency ---------------------------------------------------
    if len(ctx.date_ranges) >= 2:
        with_month = sum(1 for r in ctx.date_ranges if r.start_month is not None)
        without_month = len(ctx.date_ranges) - with_month
        if with_month and without_month:
            yield Finding(
                id="formatting.date_format_mixed",
                category=CAT, severity=Severity.SUGGESTION,
                title="Date formats are inconsistent",
                detail=(
                    f"{with_month} range(s) include a month and {without_month} give only "
                    "a year. Inconsistent dates read as careless and make tenure harder "
                    "to compare at a glance."
                ),
                fix="Use 'Mon YYYY - Mon YYYY' everywhere, or year-only everywhere.",
                evidence=[r.raw for r in ctx.date_ranges[:4]],
                penalty=6,
            )

    current_roles = [r for r in ctx.date_ranges if r.is_current]
    if len(current_roles) > 2:
        yield Finding(
            id="formatting.multiple_current",
            category=CAT, severity=Severity.SUGGESTION,
            title=f"{len(current_roles)} roles are marked as current",
            detail="More than two concurrent 'Present' roles usually means an end date was forgotten.",
            fix="Check that past roles have an end date.",
            evidence=[r.raw for r in current_roles[:4]],
            penalty=5,
        )

    # --- employment gaps ----------------------------------------------------
    significant = [g for g in ctx.gaps if g.months >= 9]
    if significant:
        largest = max(significant, key=lambda g: g.months)
        yield Finding(
            id="formatting.employment_gaps",
            category=CAT, severity=Severity.SUGGESTION,
            title=f"Unexplained gap of about {largest.months} months",
            detail=(
                f"There is a gap between roles from {largest.after_year}-"
                f"{largest.after_month:02d} to {largest.before_year}-{largest.before_month:02d}. "
                "Gaps are normal and not disqualifying, but an unexplained one invites "
                "the reader to guess."
            ),
            fix="Add a brief line covering it: study, caring responsibilities, contracting, travel, a sabbatical.",
            evidence=[g.as_dict()["from"] + " to " + g.as_dict()["to"] for g in significant[:3]],
            penalty=6,
        )

    # --- density ------------------------------------------------------------
    lines = [line for line in ctx.lines if line.strip()]
    if lines:
        overlong = [line for line in lines if len(line) > 130]
        if len(overlong) > max(3, len(lines) * 0.15):
            yield Finding(
                id="formatting.dense_lines",
                category=CAT, severity=Severity.SUGGESTION,
                title=f"{len(overlong)} very long lines of text",
                detail=(
                    "Lines running the full width of the page with no break are tiring "
                    "to read and hide the structure of what you're saying."
                ),
                fix="Break long lines into separate bullets, or widen the margins.",
                penalty=6,
            )

        blank_ratio = 1 - (len(lines) / max(1, len(ctx.lines)))
        if blank_ratio < 0.08 and len(lines) > 30:
            yield Finding(
                id="formatting.no_whitespace",
                category=CAT, severity=Severity.SUGGESTION,
                title="Very little white space between blocks",
                detail="Sections run together, which makes the resume hard to scan section by section.",
                fix="Add a blank line before each section heading and between roles.",
                penalty=5,
            )

    # --- ALL CAPS overuse ---------------------------------------------------
    caps_runs = re.findall(r"\b[A-Z]{4,}(?:\s+[A-Z]{2,}){2,}\b", ctx.text)
    if len(caps_runs) > 4:
        yield Finding(
            id="formatting.caps_overuse",
            category=CAT, severity=Severity.SUGGESTION,
            title="Long stretches of capital letters",
            detail="Blocks of capitals are measurably slower to read and come across as shouting.",
            fix="Reserve capitals for section headings; use bold for emphasis elsewhere.",
            evidence=caps_runs[:3],
            penalty=5,
        )

    # --- positives ----------------------------------------------------------
    if doc.page_count <= max_pages and 350 <= words <= 1000:
        yield Finding(
            id="formatting.well_sized",
            category=CAT, severity=Severity.POSITIVE,
            title=f"Well-sized at {doc.page_count} page(s) and {words} words",
            detail="The length is appropriate for your experience level and respects a recruiter's time.",
        )
