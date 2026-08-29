"""Rules covering which sections exist and how the resume is organised."""

from __future__ import annotations

import re
from collections.abc import Iterator

from app.data.lexicon import (
    LOW_VALUE_SECTIONS,
    RECOMMENDED_SECTIONS,
    REQUIRED_SECTIONS,
)
from app.services.rules.base import Category, Finding, ReviewContext, Severity

CAT = Category.STRUCTURE

_SECTION_GUIDANCE: dict[str, tuple[str, str]] = {
    "experience": (
        "Work experience is the section recruiters read first, and applicant tracking "
        "systems key their employment-history fields off it.",
        "Add a section headed 'Experience' listing each role with company, title and dates.",
    ),
    "education": (
        "Education is a standard screening filter, and many parsers flag a record as "
        "incomplete without it.",
        "Add an 'Education' section with degree, institution and completion year.",
    ),
    "skills": (
        "A skills section is where keyword matching does most of its work, both the "
        "software's and the recruiter's.",
        "Add a 'Skills' section listing the tools, languages and methods you actually use.",
    ),
    "summary": (
        "A short summary at the top frames everything below it and is your only chance "
        "to control the first six seconds of the read.",
        "Add a 2-3 line summary naming your role, years of experience and strongest result.",
    ),
}


def check_structure(ctx: ReviewContext) -> Iterator[Finding]:
    present = ctx.section_names

    # --- required sections --------------------------------------------------
    for name in REQUIRED_SECTIONS:
        if ctx.has_section(name):
            continue
        why, fix = _SECTION_GUIDANCE[name]
        heading_exists = any(s.name == name for s in ctx.sections)
        if heading_exists:
            # The heading is there but nothing survived under it — almost
            # always the layout scattering content during extraction.
            layout_hint = (
                " This resume's multi-column layout is the likely cause: the "
                "columns are read across each other, so the content under this "
                "heading ends up attributed elsewhere (see the ATS finding)."
                if ctx.document.multi_column_pages
                else " A parser reading this file files that content under other headings."
            )
            yield Finding(
                id=f"structure.empty_{name}",
                category=CAT, severity=Severity.CRITICAL,
                title=f"The {name} heading is there, but its content isn't under it",
                detail=(
                    f"A '{name.title()}' heading was found with no readable content "
                    f"beneath it.{layout_hint} {why}"
                ),
                fix="Move to a single-column layout so each section's content sits under its heading.",
                penalty=22,
            )
        else:
            yield Finding(
                id=f"structure.missing_{name}",
                category=CAT, severity=Severity.CRITICAL,
                title=f"No {name} section found",
                detail=(
                    f"No section headed '{name.title()}' (or a recognised equivalent) "
                    f"could be found. {why}"
                ),
                fix=fix,
                penalty=22,
            )

    for name in RECOMMENDED_SECTIONS:
        if not ctx.has_section(name):
            why, fix = _SECTION_GUIDANCE[name]
            yield Finding(
                id=f"structure.missing_{name}",
                category=CAT, severity=Severity.WARNING,
                title=f"No {name} section",
                detail=why,
                fix=fix,
                penalty=10,
            )

    # --- ordering -----------------------------------------------------------
    order = [s.name for s in ctx.sections if s.name in present]
    if "experience" in order and "education" in order:
        exp_at, edu_at = order.index("experience"), order.index("education")
        months = ctx.experience_months
        # Education first is right for new graduates, wrong once you have a career.
        if edu_at < exp_at and months > 36:
            yield Finding(
                id="structure.education_before_experience",
                category=CAT, severity=Severity.WARNING,
                title="Education is placed above work experience",
                detail=(
                    "With several years of work history, experience should come first. "
                    "Education-first ordering signals a recent graduate and buries your "
                    "strongest material below the fold."
                ),
                fix="Move the education section below work experience.",
                penalty=12,
            )

    if "summary" in order and order.index("summary") > 1:
        yield Finding(
            id="structure.summary_not_first",
            category=CAT, severity=Severity.SUGGESTION,
            title="Summary isn't at the top",
            detail="A summary only works if it is the first thing read after your name.",
            fix="Move the summary directly beneath the contact header.",
            penalty=6,
        )

    # --- low-value sections -------------------------------------------------
    wasteful = [name for name in LOW_VALUE_SECTIONS if name in present]
    if wasteful:
        yield Finding(
            id="structure.low_value_sections",
            category=CAT, severity=Severity.SUGGESTION,
            title=f"Low-value section{'s' if len(wasteful) > 1 else ''}: {', '.join(wasteful)}",
            detail=(
                "'References available on request' is assumed, and hobbies rarely change "
                "a hiring decision. Both consume space that could carry results."
            ),
            fix=f"Remove the {' and '.join(wasteful)} section and use the space for achievements.",
            evidence=wasteful,
            penalty=5,
        )

    # --- section balance ----------------------------------------------------
    experience = ctx.section("experience")
    if experience and experience.word_count:
        total_words = sum(s.word_count for s in ctx.sections) or 1
        share = experience.word_count / total_words
        if share < 0.35:
            yield Finding(
                id="structure.experience_thin",
                category=CAT, severity=Severity.WARNING,
                title="Work experience is thin relative to the rest",
                detail=(
                    f"Only {share:.0%} of the resume's text sits in the experience section. "
                    "Recruiters spend most of their time there, so it should be the bulk "
                    "of the document."
                ),
                fix="Expand each role with 3-5 achievement bullets, and trim other sections.",
                penalty=10,
            )

    # --- skills section quality --------------------------------------------
    skills = ctx.section("skills")
    if skills and skills.word_count:
        if skills.word_count > 120:
            yield Finding(
                id="structure.skills_bloated",
                category=CAT, severity=Severity.SUGGESTION,
                title="Skills section is very long",
                detail=(
                    f"The skills section runs to {skills.word_count} words. Long "
                    "undifferentiated lists read as padding and dilute the skills that "
                    "actually matter for the role."
                ),
                fix="Group skills into 3-5 labelled clusters and drop anything you wouldn't be interviewed on.",
                penalty=6,
            )
        skills_flat = re.sub(r"\s+", " ", skills.text.lower())
        if any(
            token in skills_flat
            for token in ("microsoft word", "ms word", "email", "internet", "typing", "windows xp")
        ):
            yield Finding(
                id="structure.skills_obsolete",
                category=CAT, severity=Severity.SUGGESTION,
                title="Skills list includes assumed basics",
                detail=(
                    "Listing things like Microsoft Word or email as skills signals a thin "
                    "skill set rather than a broad one."
                ),
                fix="Remove baseline computer literacy and list role-specific tools instead.",
                penalty=5,
            )

    # --- positives ----------------------------------------------------------
    if all(ctx.has_section(name) for name in REQUIRED_SECTIONS) and ctx.has_section("summary"):
        yield Finding(
            id="structure.complete",
            category=CAT, severity=Severity.POSITIVE,
            title="All expected sections are present",
            detail="Summary, experience, education and skills were all found and labelled clearly.",
        )
