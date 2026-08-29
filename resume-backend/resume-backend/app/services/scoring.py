"""Turn findings into category scores and one overall score."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.rules.base import (
    CATEGORY_DESCRIPTIONS,
    CATEGORY_LABELS,
    CATEGORY_WEIGHTS,
    Category,
    Finding,
    Severity,
)

# Bands used for the headline verdict.
_BANDS: tuple[tuple[float, str, str], ...] = (
    (85, "excellent", "This resume is in strong shape and ready to send."),
    (70, "good", "A solid resume with a few clear opportunities to sharpen it."),
    (55, "fair", "The fundamentals are there, but several issues are costing you interviews."),
    (35, "needs_work", "This resume needs substantial revision before applying."),
    (0, "poor", "Significant rework is needed across most areas."),
)


@dataclass
class CategoryScore:
    category: Category
    score: float
    weight: float
    finding_count: int = 0
    critical_count: int = 0
    penalties: float = 0.0
    applicable: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "category": str(self.category),
            "label": CATEGORY_LABELS[self.category],
            "description": CATEGORY_DESCRIPTIONS[self.category],
            "score": round(self.score, 1),
            "weight": round(self.weight, 1),
            "finding_count": self.finding_count,
            "critical_count": self.critical_count,
            "applicable": self.applicable,
        }


@dataclass
class ScoreResult:
    overall: float
    band: str
    verdict: str
    categories: list[CategoryScore] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "overall": round(self.overall, 1),
            "band": self.band,
            "verdict": self.verdict,
            "categories": [c.as_dict() for c in self.categories],
        }


def _band(score: float) -> tuple[str, str]:
    for threshold, band, verdict in _BANDS:
        if score >= threshold:
            return band, verdict
    return _BANDS[-1][1], _BANDS[-1][2]


def score_findings(
    findings: list[Finding], *, applicable: set[Category] | None = None
) -> ScoreResult:
    """Each category starts at 100 and loses its findings' penalties.

    Categories that don't apply to this run (job match with no job description)
    are excluded, and their weight is redistributed over the rest, so the
    overall score always means the same thing.
    """
    applicable = applicable if applicable is not None else set(Category)

    categories: list[CategoryScore] = []
    for category in Category:
        in_scope = category in applicable
        relevant = [f for f in findings if f.category is category]
        penalties = sum(f.penalty for f in relevant)
        score = max(0.0, min(100.0, 100.0 - penalties))
        categories.append(
            CategoryScore(
                category=category,
                score=score if in_scope else 0.0,
                weight=CATEGORY_WEIGHTS[category],
                finding_count=sum(1 for f in relevant if f.severity is not Severity.POSITIVE),
                critical_count=sum(1 for f in relevant if f.severity is Severity.CRITICAL),
                penalties=penalties,
                applicable=in_scope,
            )
        )

    scoring = [c for c in categories if c.applicable]
    total_weight = sum(c.weight for c in scoring) or 1.0
    overall = sum(c.score * c.weight for c in scoring) / total_weight

    band, verdict = _band(overall)
    return ScoreResult(overall=overall, band=band, verdict=verdict, categories=categories)


# Order findings so the most actionable appear first.
_SEVERITY_RANK = {
    Severity.CRITICAL: 0,
    Severity.WARNING: 1,
    Severity.SUGGESTION: 2,
    Severity.POSITIVE: 3,
}


def sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(
        findings,
        key=lambda f: (_SEVERITY_RANK[f.severity], -f.penalty, str(f.category), f.id),
    )


def priority_fixes(findings: list[Finding], limit: int = 5) -> list[Finding]:
    """The highest-leverage changes: biggest penalty first, positives excluded."""
    actionable = [f for f in findings if f.severity is not Severity.POSITIVE and f.penalty > 0]
    ranked = sorted(
        actionable,
        key=lambda f: (-(f.penalty * CATEGORY_WEIGHTS[f.category] / 100.0), _SEVERITY_RANK[f.severity]),
    )
    return ranked[:limit]
