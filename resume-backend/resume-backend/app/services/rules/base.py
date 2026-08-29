"""Shared types for the deterministic review rules.

Each rule receives a fully-parsed ``ReviewContext`` and returns ``Finding``s.
A finding carries a penalty in points, deducted from its category's 100-point
budget, so every score the user sees can be traced back to specific evidence.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.extraction import ExtractedDocument
    from app.services.parsing import Bullet, ContactInfo, DateRange, TimelineGap
    from app.services.sectioning import Section


class Severity(StrEnum):
    CRITICAL = "critical"      # will actively cost interviews
    WARNING = "warning"        # meaningfully weakens the resume
    SUGGESTION = "suggestion"  # worth doing, lower impact
    POSITIVE = "positive"      # done well; never carries a penalty


class Category(StrEnum):
    CONTACT = "contact"
    STRUCTURE = "structure"
    IMPACT = "impact"
    ATS = "ats"
    FORMATTING = "formatting"
    KEYWORDS = "keywords"


CATEGORY_LABELS: dict[Category, str] = {
    Category.CONTACT: "Contact & Header",
    Category.STRUCTURE: "Structure & Sections",
    Category.IMPACT: "Impact & Writing",
    Category.ATS: "ATS Compatibility",
    Category.FORMATTING: "Formatting & Length",
    Category.KEYWORDS: "Job Match",
}

CATEGORY_DESCRIPTIONS: dict[Category, str] = {
    Category.CONTACT: "Whether a recruiter can identify and reach you in seconds.",
    Category.STRUCTURE: "Whether the expected sections are present and easy to scan.",
    Category.IMPACT: "Whether your bullets show measurable results rather than duties.",
    Category.ATS: "Whether applicant tracking software can read the file correctly.",
    Category.FORMATTING: "Whether the length and layout respect a recruiter's time.",
    Category.KEYWORDS: "How closely the resume matches the target job description.",
}

# Relative weight of each category in the overall score.
CATEGORY_WEIGHTS: dict[Category, float] = {
    Category.CONTACT: 10.0,
    Category.STRUCTURE: 15.0,
    Category.IMPACT: 25.0,
    Category.ATS: 20.0,
    Category.FORMATTING: 15.0,
    Category.KEYWORDS: 15.0,
}


@dataclass
class Finding:
    id: str
    category: Category
    severity: Severity
    title: str
    detail: str
    fix: str = ""
    evidence: list[str] = field(default_factory=list)
    penalty: float = 0.0
    # Canonical resume section this finding is about ("header", "summary",
    # "experience", ...); None means it concerns the whole document.
    section: str | None = None

    def __post_init__(self) -> None:
        if self.severity is Severity.POSITIVE:
            self.penalty = 0.0
        self.penalty = max(0.0, float(self.penalty))
        # Keep evidence quotable but bounded.
        self.evidence = [e.strip()[:240] for e in self.evidence if e and e.strip()][:5]

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "category": str(self.category),
            "category_label": CATEGORY_LABELS[self.category],
            "severity": str(self.severity),
            "title": self.title,
            "detail": self.detail,
            "fix": self.fix,
            "evidence": self.evidence,
            "penalty": round(self.penalty, 2),
            "section": self.section,
        }


@dataclass
class ReviewContext:
    """Everything the rules need, parsed exactly once."""

    text: str
    sections: list["Section"]
    contact: "ContactInfo"
    bullets: list["Bullet"]
    date_ranges: list["DateRange"]
    gaps: list["TimelineGap"]
    document: "ExtractedDocument"
    today: date
    target_role: str | None = None
    job_description: str | None = None

    def section(self, name: str) -> "Section | None":
        from app.services.sectioning import find_section

        return find_section(self.sections, name)

    def has_section(self, name: str) -> bool:
        section = self.section(name)
        return section is not None and section.word_count > 0

    @property
    def section_names(self) -> set[str]:
        return {s.name for s in self.sections if s.name not in ("header", "unknown")}

    @property
    def experience_bullets(self) -> list["Bullet"]:
        """Bullets the impact rules should judge.

        Prefer work-section bullets, but only when section attribution looks
        trustworthy: in a scrambled layout (multi-column PDFs) most bullets
        land outside the experience section, and judging the stray few would
        misrepresent the resume. In that case judge every bullet.
        """
        preferred = [b for b in self.bullets if b.section in ("experience", "projects")]
        if preferred and len(preferred) >= max(4, 0.4 * len(self.bullets)):
            return preferred
        return self.bullets or preferred

    @property
    def flat_text(self) -> str:
        """Lowercased text with all whitespace collapsed to single spaces.

        PDFs hard-wrap lines, so a phrase like "proven track record" is often
        split across a newline. Phrase matching must not care.
        """
        import re

        return re.sub(r"\s+", " ", self.text.lower())

    @property
    def experience_ranges(self) -> list["DateRange"]:
        """Date ranges from work sections only — education is not tenure."""
        work = [r for r in self.date_ranges if r.section in ("experience", "projects")]
        # If nothing was tagged (unusual layout), fall back to everything.
        return work or self.date_ranges

    @property
    def experience_months(self) -> int:
        from app.services.parsing import total_experience_months

        return total_experience_months(self.experience_ranges, self.today)

    @property
    def has_job_description(self) -> bool:
        return bool(self.job_description and self.job_description.strip())

    @property
    def lines(self) -> list[str]:
        return self.text.split("\n")


Rule = Callable[[ReviewContext], Iterable[Finding]]
