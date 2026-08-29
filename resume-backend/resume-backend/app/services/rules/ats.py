"""Rules covering machine readability — will an ATS parse this file correctly?"""

from __future__ import annotations

import re
from collections.abc import Iterator

from app.data.lexicon import SECTION_SYNONYMS
from app.services.rules.base import Category, Finding, ReviewContext, Severity

CAT = Category.ATS

# Headings a parser reliably recognises, versus creative rewrites of them.
_STANDARD_HEADINGS = {syn for syns in SECTION_SYNONYMS.values() for syn in syns}

_CREATIVE_HEADINGS = {
    "where i've been", "my journey", "the story so far", "what i do",
    "my toolkit", "brain dump", "career highlights reel", "my superpowers",
    "things i'm good at", "who i am", "the basics", "let's talk",
}


def check_ats(ctx: ReviewContext) -> Iterator[Finding]:
    doc = ctx.document

    # --- unreadable file ----------------------------------------------------
    if doc.is_scanned:
        yield Finding(
            id="ats.no_text_layer",
            category=CAT, severity=Severity.CRITICAL,
            title="The file has almost no selectable text",
            detail=(
                "Very little machine-readable text was found. The resume looks like a "
                "scan or an image export. Applicant tracking systems do not run OCR, so "
                "this file will be read as effectively blank."
            ),
            fix="Export a text-based PDF directly from Word, Google Docs or Pages instead of an image or scan.",
            penalty=60,
        )

    # --- multi-column layout ------------------------------------------------
    if doc.multi_column_pages:
        yield Finding(
            id="ats.multi_column",
            category=CAT, severity=Severity.CRITICAL,
            title=f"Multi-column layout detected on {doc.multi_column_pages} page(s)",
            detail=(
                "Side-by-side columns are the most common cause of scrambled resume "
                "parsing: many systems read straight across the page, interleaving the "
                "sidebar into your job descriptions and producing nonsense."
            ),
            fix="Move to a single-column layout. Keep the visual polish in typography and spacing instead.",
            penalty=30,
        )

    # --- tables -------------------------------------------------------------
    if doc.has_tables:
        yield Finding(
            id="ats.tables",
            category=CAT, severity=Severity.WARNING,
            title=f"Content sits inside {doc.table_count} table(s)",
            detail=(
                "Table cells are frequently flattened out of order, merged, or dropped "
                "entirely during parsing. Skills grids and two-column date layouts are "
                "the usual culprits."
            ),
            fix="Replace tables with plain paragraphs and bullet lists.",
            penalty=18,
        )

    # --- header / footer ----------------------------------------------------
    if doc.has_header_footer_text:
        yield Finding(
            id="ats.header_footer",
            category=CAT, severity=Severity.WARNING,
            title="Contact details appear in a page header or footer",
            detail=(
                "Many parsers ignore the header and footer regions completely. Anything "
                "placed there, often the email and phone number, can vanish."
            ),
            fix="Move all contact details into the body of the first page.",
            penalty=16,
        )

    # --- images -------------------------------------------------------------
    if doc.image_count >= 3:
        yield Finding(
            id="ats.image_heavy",
            category=CAT, severity=Severity.WARNING,
            title=f"{doc.image_count} images or graphics embedded",
            detail=(
                "Skill-rating bars, icons and charts carry no text. To a parser they are "
                "blank space, and to a recruiter a five-dot rating means nothing without "
                "a scale."
            ),
            fix="Replace graphics with text. State proficiency in words, e.g. 'Python: 6 years, production'.",
            penalty=12,
        )
    elif doc.image_count and doc.image_count < 3:
        yield Finding(
            id="ats.images_present",
            category=CAT, severity=Severity.SUGGESTION,
            title="Embedded image(s) detected",
            detail="Images are invisible to resume parsers and to screen readers.",
            fix="Make sure no information exists only inside an image.",
            penalty=4,
        )

    # --- non-standard headings ---------------------------------------------
    creative = [
        s.heading for s in ctx.sections
        if s.heading and s.heading.strip().lower().rstrip(":") in _CREATIVE_HEADINGS
    ]
    unlabelled = [s.heading for s in ctx.sections if s.name == "unknown" and s.heading]
    if creative:
        yield Finding(
            id="ats.creative_headings",
            category=CAT, severity=Severity.WARNING,
            title="Section headings a parser won't recognise",
            detail=(
                "Headings like these are not mapped to any standard field, so the content "
                "beneath them is often filed as uncategorised text."
            ),
            fix="Use conventional headings: Summary, Experience, Education, Skills, Projects.",
            evidence=creative[:4],
            penalty=14,
        )
    elif len(unlabelled) >= 3:
        yield Finding(
            id="ats.unrecognised_headings",
            category=CAT, severity=Severity.SUGGESTION,
            title=f"{len(unlabelled)} section heading(s) weren't recognised",
            detail=(
                "These headings don't match the names parsers look for, so their content "
                "may not be mapped to the right field."
            ),
            fix="Rename them to standard section names where you can.",
            evidence=unlabelled[:4],
            penalty=7,
        )

    # --- special characters -------------------------------------------------
    exotic = re.findall(r"[^\x00-\x7FÀ-ɏ•–—’“”\s]", ctx.text)
    if len(exotic) > 12:
        sample = "".join(dict.fromkeys(exotic))[:10]
        yield Finding(
            id="ats.exotic_characters",
            category=CAT, severity=Severity.SUGGESTION,
            title="Unusual symbols or decorative glyphs in the text",
            detail=(
                f"{len(exotic)} characters outside the normal range were found (e.g. {sample}). "
                "Icon fonts and decorative dingbats often come through as garbage or boxes."
            ),
            fix="Replace decorative glyphs with plain text labels.",
            evidence=[sample],
            penalty=6,
        )

    # --- date readability ---------------------------------------------------
    if ctx.has_section("experience") and not ctx.date_ranges:
        yield Finding(
            id="ats.no_parsable_dates",
            category=CAT, severity=Severity.CRITICAL,
            title="No employment dates could be parsed",
            detail=(
                "No date ranges in a recognisable format were found. Tenure is a primary "
                "screening filter, and a record with no dates often fails an automatic "
                "'years of experience' check."
            ),
            fix="Write dates as 'Mar 2021 - Present' or '03/2021 - 06/2024' next to each role.",
            penalty=25,
        )

    # --- positives ----------------------------------------------------------
    if not any([doc.is_scanned, doc.multi_column_pages, doc.has_tables,
                doc.has_header_footer_text, doc.image_count >= 3]):
        yield Finding(
            id="ats.clean_layout",
            category=CAT, severity=Severity.POSITIVE,
            title="Layout is parser-friendly",
            detail=(
                "Single column, no tables, no text hidden in headers or images. This "
                "file should survive automated parsing intact."
            ),
        )
