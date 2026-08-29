"""Unit tests for the deterministic review engine."""

from __future__ import annotations

from datetime import date

import pytest

from app.services.analyzer import build_context, review
from app.services.extraction import ExtractionError, clean_text, extract_document
from app.services.parsing import extract_contact, extract_date_ranges, find_gaps
from app.services.rules.base import Category, Severity
from app.services.rules.keywords import _stem, build_keyword_report
from app.services.sectioning import find_section, match_section_name, split_sections

TODAY = date(2026, 8, 28)

GOOD_RESUME = """\
JANE MARTINEZ
San Francisco, CA | jane.martinez@example.com | (415) 555-0142
linkedin.com/in/janemartinez | github.com/janemartinez

PROFESSIONAL SUMMARY
Backend engineer with 6 years building payment infrastructure at scale.

WORK EXPERIENCE

Senior Backend Engineer
Payments Inc, San Francisco, CA | Mar 2021 - Present
• Led migration of the ledger service to PostgreSQL, cutting p99 latency by 43%
• Scaled the payouts pipeline to process $2.1B annually across 14 markets
• Mentored 4 junior engineers; 3 were promoted within 18 months
• Reduced infrastructure spend by 27% by rightsizing Kubernetes workloads

Backend Engineer
FinTech Startup, Remote | Jun 2018 - Feb 2021
• Built a fraud detection service in Python that reduced chargebacks by 31%
• Designed REST APIs consumed by 12 internal teams
• Automated deployment, cutting release time from 4 hours to 20 minutes

EDUCATION
B.S. Computer Science, University of California, Berkeley | 2014 - 2018

TECHNICAL SKILLS
Python, Go, PostgreSQL, Redis, Kubernetes, AWS, Terraform, gRPC, Kafka
"""

WEAK_RESUME = """\
my resume

Objective
I am a hard working team player and a self-starter with a proven track record.

Experience
Some Company
• Responsible for various tasks
• Helped with stuff
• Worked on things as needed

Education
A degree
"""


def _doc(text: str, name: str = "r.txt"):
    return extract_document(name, text.encode())


# --------------------------------------------------------------------------- #
# Extraction
# --------------------------------------------------------------------------- #
def test_clean_text_normalises_bullets_and_ligatures():
    out = clean_text("• ﬁrst item\r\n\n\n\n● second")
    assert "first item" in out
    assert out.count("•") == 2
    assert "\r" not in out
    assert "\n\n\n" not in out


def test_legacy_doc_is_rejected_with_guidance():
    with pytest.raises(ExtractionError, match="docx"):
        extract_document("old.doc", b"x" * 500)


def test_empty_and_tiny_files_are_rejected():
    with pytest.raises(ExtractionError):
        extract_document("a.txt", b"")
    with pytest.raises(ExtractionError):
        extract_document("a.txt", b"too short")


# --------------------------------------------------------------------------- #
# Sectioning
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "heading,expected",
    [
        ("WORK EXPERIENCE", "experience"),
        ("Professional Experience", "experience"),
        ("Education:", "education"),
        ("Core Competencies", "skills"),
        ("Tech Stack", "skills"),
        ("Random Sentence That Is Long And Not A Heading At All", None),
    ],
)
def test_heading_synonyms(heading, expected):
    assert match_section_name(heading) == expected


def test_job_titles_do_not_split_the_experience_section():
    sections = split_sections(clean_text(GOOD_RESUME))
    experience = find_section(sections, "experience")
    assert experience is not None
    # Both roles must live inside the one experience section.
    assert "Senior Backend Engineer" in experience.text
    assert "FinTech Startup" in experience.text
    assert experience.word_count > 80


def test_header_section_holds_contact_block():
    sections = split_sections(clean_text(GOOD_RESUME))
    header = find_section(sections, "header")
    assert header is not None
    assert "jane.martinez@example.com" in header.text


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def test_contact_extraction():
    text = clean_text(GOOD_RESUME)
    contact = extract_contact(text, split_sections(text))
    assert contact.name == "JANE MARTINEZ"
    assert contact.emails == ["jane.martinez@example.com"]
    assert contact.phones
    assert contact.linkedin and "janemartinez" in contact.linkedin
    assert contact.github
    # The surname must not be mistaken for a city.
    assert contact.location == "San Francisco, CA"


def test_education_dates_are_not_counted_as_tenure():
    ctx = build_context(_doc(GOOD_RESUME), today=TODAY)
    sections = {r.section for r in ctx.date_ranges}
    assert "education" in sections
    # 2018-2026 of work, not 2014-2026.
    assert 7.5 <= ctx.experience_months / 12 <= 8.6


def test_gap_detection():
    ranges = extract_date_ranges("Jan 2015 - Jun 2017\nJan 2019 - Present")
    gaps = find_gaps(ranges, TODAY)
    assert len(gaps) == 1
    assert gaps[0].months >= 18


# --------------------------------------------------------------------------- #
# Rules and scoring
# --------------------------------------------------------------------------- #
def test_strong_resume_scores_above_weak_one():
    good = review(_doc(GOOD_RESUME), today=TODAY)
    weak = review(_doc(WEAK_RESUME), today=TODAY)
    assert good.score.overall > weak.score.overall + 25


def test_weak_resume_flags_the_expected_problems():
    result = review(_doc(WEAK_RESUME), today=TODAY)
    ids = {f.id for f in result.findings}
    assert "impact.weak_openers" in ids
    assert "impact.cliches" in ids
    assert "impact.filler_phrases" in ids
    assert "contact.email_missing" in ids
    assert any(f.severity is Severity.CRITICAL for f in result.findings)


def test_strong_resume_earns_positive_findings():
    result = review(_doc(GOOD_RESUME), today=TODAY)
    positives = {f.id for f in result.findings if f.severity is Severity.POSITIVE}
    assert "impact.well_quantified" in positives
    assert "contact.complete" in positives


def test_scores_stay_in_range_and_categories_are_complete():
    result = review(_doc(WEAK_RESUME), today=TODAY)
    assert 0 <= result.score.overall <= 100
    assert {c.category for c in result.score.categories} == set(Category)
    for category in result.score.categories:
        assert 0 <= category.score <= 100


def test_job_match_is_excluded_without_a_job_description():
    result = review(_doc(GOOD_RESUME), today=TODAY)
    keywords = next(c for c in result.score.categories if c.category is Category.KEYWORDS)
    assert keywords.applicable is False
    assert result.keyword_report is None


def test_priorities_are_ordered_by_weighted_impact():
    result = review(_doc(WEAK_RESUME), today=TODAY)
    assert result.priorities
    assert all(f.severity is not Severity.POSITIVE for f in result.priorities)
    assert len(result.priorities) <= 5


def test_one_broken_rule_does_not_fail_the_review(monkeypatch):
    import app.services.analyzer as analyzer

    def exploding_rule(ctx):
        raise RuntimeError("boom")

    monkeypatch.setattr(analyzer, "RULES", (exploding_rule, *analyzer.RULES))
    result = analyzer.review(_doc(GOOD_RESUME), today=TODAY)
    assert "exploding_rule" in result.rule_errors
    assert result.score.overall > 0


# --------------------------------------------------------------------------- #
# Keyword matching
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "word,stem",
    [("mentoring", "mentor"), ("mentored", "mentor"), ("managing", "manag"),
     ("managed", "manag"), ("kubernetes", "kubernetes"), ("leading", "lead")],
)
def test_stemming_is_consistent(word, stem):
    assert _stem(word) == stem


def test_comma_separated_skills_are_not_merged_into_one_term():
    ctx = build_context(
        _doc(GOOD_RESUME),
        job_description="Requirements:\n• Experience with PostgreSQL, Kafka and Docker",
        today=TODAY,
    )
    report = build_keyword_report(ctx)
    assert report is not None
    matched = {m["term"] for m in report["matched"]}
    missing = {m["term"] for m in report["missing"]}
    # The resume has PostgreSQL and Kafka but not Docker.
    assert "postgresql" in matched
    assert "kafka" in matched
    assert "docker" in missing
    assert not any(" " in term and "postgresql" in term for term in missing)


def test_job_description_boilerplate_is_not_treated_as_a_skill():
    ctx = build_context(
        _doc(GOOD_RESUME),
        job_description="We require strong experience and demonstrated expertise. "
                        "Must have knowledge of Rust and familiarity with Elixir.",
        today=TODAY,
    )
    report = build_keyword_report(ctx)
    terms = {m["term"] for m in report["matched"]} | {m["term"] for m in report["missing"]}
    for boilerplate in ("require", "experience", "expertise", "knowledge", "familiar"):
        assert boilerplate not in terms
    assert "rust" in terms and "elixir" in terms


# --------------------------------------------------------------------------- #
# PDF line-wrapping robustness
# --------------------------------------------------------------------------- #
WRAPPED_RESUME = """\
JANE DOE
jane@example.com | (415) 555-0142 | linkedin.com/in/janedoe | San Francisco, CA

SUMMARY
Engineer with a proven track
record and excellent communication
skills.

EXPERIENCE
Engineer, Acme | Jan 2020 - Present
• Responsible for
  various tasks
• Built a thing that cut costs by 20%

EDUCATION
BS, Somewhere | 2016 - 2020

SKILLS
Python, SQL
"""


def test_phrases_split_across_line_breaks_are_still_caught():
    """PDFs hard-wrap lines, so a cliché often straddles a newline."""
    result = review(_doc(WRAPPED_RESUME), today=TODAY)
    cliches = next(f for f in result.findings if f.id == "impact.cliches")
    assert "proven track record" in cliches.evidence
    assert "excellent communication skills" in cliches.evidence
    fillers = next(f for f in result.findings if f.id == "impact.filler_phrases")
    assert "responsible for" in fillers.evidence


def test_flat_text_collapses_whitespace():
    ctx = build_context(_doc(WRAPPED_RESUME), today=TODAY)
    assert "proven track record" in ctx.flat_text
    assert "\n" not in ctx.flat_text


# --------------------------------------------------------------------------- #
# Multi-column coherence (real-resume regression)
# --------------------------------------------------------------------------- #
INTERLEAVED_RESUME = """\
THULAN EXAMPLE
OBJECTIVE
Cloud leader with 8+ years securing platforms and
CONTACT
governance programs aligned with NIST.
 thulan@example.com across VMware and Huawei Cloud.

EXPERIENCE

SKILLS
Lead - Cloud DevOps Apr 2023
Dialog Example PLC
Security Architecture
• Lead security governance of enterprise cloud platforms including
ISO 27001: 2013 / 2022, VMware Cloud Foundation and Huawei Cloud Stack
• Conduct security architecture reviews for new cloud services,
and technology transformation projects.
• Implement and maintain controls aligned with NIST and internal
technologies.
• Integrate cloud platforms with enterprise identity and PAM
• Reviewed Statements of Work to ensure requirements were embedded
• Drove root cause analysis and continuous improvement of response
Engineer - IP Networks Jun 2017 - Aug 2018
• Operated backbone routing across 40 sites with 99.98% availability
• Automated config audits, cutting review time by 60%

EDUCATION
BSc Engineering, Example University | 2013 - 2017
"""


def test_prose_fragments_do_not_become_section_headings():
    sections = split_sections(clean_text(INTERLEAVED_RESUME))
    headings = [s.heading for s in sections]
    assert "and technology transformation projects." not in headings
    assert "technologies." not in headings


def test_empty_experience_heading_gets_the_layout_diagnosis():
    doc = extract_document("r.txt", INTERLEAVED_RESUME.encode())
    doc.multi_column_pages = 1  # what the PDF path would have detected
    result = review(doc, today=TODAY)
    ids = {f.id for f in result.findings}
    # The heading exists, so the finding must be "empty", never "missing".
    assert "structure.missing_experience" not in ids
    assert "structure.empty_experience" in ids
    empty = next(f for f in result.findings if f.id == "structure.empty_experience")
    assert "multi-column" in empty.detail


def test_impact_rules_judge_all_bullets_when_attribution_is_scrambled():
    doc = extract_document("r.txt", INTERLEAVED_RESUME.encode())
    result = review(doc, today=TODAY)
    ctx = build_context(doc, today=TODAY)
    # Most bullets sit outside the (empty) experience section, so the judged
    # set must be the full set, not the stray few.
    assert len(ctx.experience_bullets) == len(ctx.bullets) >= 8
    metrics = next(
        (f for f in result.findings if f.id in ("impact.no_metrics", "impact.few_metrics")), None
    )
    if metrics is not None:
        assert f"of {len(ctx.bullets)} bullets" in f"{metrics.title} {metrics.detail}"


def test_priorities_carry_overall_gain_and_projection():
    from app.services.analyzer import enrich_priorities

    result = review(_doc(WEAK_RESUME), today=TODAY)
    priorities, projected = enrich_priorities(result.priorities, result.score.overall)
    assert priorities and all("overall_gain" in p for p in priorities)
    assert all(p["overall_gain"] >= 0 for p in priorities)
    assert result.score.overall < projected <= 100


# --------------------------------------------------------------------------- #
# Section attribution (report grouped by the resume's own sections)
# --------------------------------------------------------------------------- #
def test_findings_are_attributed_to_resume_sections():
    result = review(_doc(WEAK_RESUME), today=TODAY)
    by_id = {f.id: f for f in result.findings}

    assert by_id["contact.email_missing"].section == "header"
    # The clichés live in the summary/objective block.
    assert by_id["impact.cliches"].section == "summary"
    # The weak openers are experience bullets.
    assert by_id["impact.weak_openers"].section == "experience"
    # Word count concerns the whole document.
    assert by_id["formatting.too_short"].section is None


def test_empty_section_findings_point_at_their_section():
    doc = extract_document("r.txt", INTERLEAVED_RESUME.encode())
    doc.multi_column_pages = 1
    result = review(doc, today=TODAY)
    empty = next(f for f in result.findings if f.id == "structure.empty_experience")
    assert empty.section == "experience"
    layout = next(f for f in result.findings if f.id == "ats.multi_column")
    assert layout.section is None  # the layout is a whole-document problem


def test_date_findings_land_on_experience():
    result = review(_doc(GOOD_RESUME), today=TODAY)
    dates = next((f for f in result.findings if f.id == "formatting.date_format_mixed"), None)
    if dates is not None:
        assert dates.section == "experience"
