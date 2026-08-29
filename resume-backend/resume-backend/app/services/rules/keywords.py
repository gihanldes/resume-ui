"""Match the resume against a target job description.

The goal is not naive keyword stuffing: it is telling the candidate which
requirements the job actually emphasises and which of those their resume
currently gives no evidence for.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field

from app.data.lexicon import (
    ALIAS_TO_CANONICAL,
    KEYWORD_BLOCKLIST,
    SKILL_ALIASES,
    STOPWORDS,
)
from app.services.rules.base import Category, Finding, ReviewContext, Severity

CAT = Category.KEYWORDS

@dataclass
class KeywordMatch:
    term: str
    weight: float
    in_resume: bool
    variants: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "term": self.term,
            "weight": round(self.weight, 2),
            "in_resume": self.in_resume,
            "variants": self.variants,
        }


_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#./-]*")
# Bigrams must not be formed across these: "PostgreSQL, Kafka" is two skills,
# not one term called "postgresql kafka".
_CHUNK_SPLIT_RE = re.compile(r"[,;:|/()\[\]{}]|\.\s|\band\b|\bor\b|\bwith\b|\bin\b")

# Requirement lines carry far more signal than boilerplate ones.
_REQUIREMENT_MARKERS = (
    "require", "must have", "you have", "you'll need", "qualification",
    "experience with", "experience in", "proficien", "expertise", "familiar",
    "knowledge of", "skilled", "background in", "demonstrated",
)

# Words that describe *how* a requirement is phrased, never the requirement itself.
_JD_BOILERPLATE: frozenset[str] = frozenset(
    """require required requirement requires must need needed needs expertise
    expert familiar familiarity knowledge knowledgeable proficient proficiency
    demonstrated demonstrable background skilled skill experience experienced
    production nice good great strong solid deep hands hands-on plus bonus
    ideally preferably essential desirable minimum maximum least ability
    understanding understand comfortable passion passionate track record
    ownership owner drive driven deliver delivery quality best practice
    practices standard standards day daily weekly monthly annual""".split()
)

# Words ending in "s" that are already singular, plus acronyms we must not stem.
_PROTECTED_TOKENS: frozenset[str] = frozenset(
    """kubernetes aws devops mlops dataops analytics statistics mathematics
    physics economics logistics ethics redis jenkins kafka nodejs rails ios
    macos https cors saas paas iaas news series sales operations communications
    graphics systems windows tls tests css js ts sass less express keras
    numerics genomics robotics linguistics""".split()
)


def _stem(token: str) -> str:
    """Collapse inflections so 'mentoring', 'mentored' and 'mentor' all match.

    Consistency between the two sides matters far more than linguistic
    correctness here; the user never sees a stem, only the surface form.
    """
    if token in _PROTECTED_TOKENS or len(token) <= 3 or not token.isalpha():
        return token
    if token.endswith("ies") and len(token) > 4:
        token = token[:-3] + "y"
    elif token.endswith("ing") and len(token) > 5:
        token = token[:-3]
        if len(token) > 2 and token[-1] == token[-2] and token[-1] not in "lsz":
            token = token[:-1]
    elif token.endswith("ed") and len(token) > 4:
        token = token[:-2]
        if len(token) > 2 and token[-1] == token[-2] and token[-1] not in "lsz":
            token = token[:-1]
    elif token.endswith("es") and len(token) > 4 and token[-3] in "sxzhio":
        token = token[:-2]
    elif token.endswith("s") and not token.endswith("ss") and len(token) > 3:
        token = token[:-1]
    # Normalise the silent 'e' so manage/managing/managed all land on "manag".
    if len(token) > 3 and token.endswith("e"):
        token = token[:-1]
    return token


def _normalise(token: str) -> str:
    token = token.lower().strip(".,;:!?()[]{}\"'")
    # Keep c++ / c# / .net / node.js intact; strip trailing punctuation elsewhere.
    if token in {"c++", "c#", ".net", "node.js", "vue.js", "react.js"}:
        return token
    return token.rstrip("./-")


def _is_noise(token: str) -> bool:
    return (
        len(token) < 2
        or token.isdigit()
        or token in STOPWORDS
        or token in KEYWORD_BLOCKLIST
        or token in _JD_BOILERPLATE
    )


def _key(term: str) -> str:
    """Canonical matching key for a one- or two-word term."""
    return " ".join(_stem(part) for part in term.split())


def _chunks(line: str) -> list[list[str]]:
    """Token runs that may legitimately form a bigram."""
    runs: list[list[str]] = []
    for piece in _CHUNK_SPLIT_RE.split(line.lower()):
        tokens = [t for t in (_normalise(t) for t in _TOKEN_RE.findall(piece)) if t]
        if tokens:
            runs.append(tokens)
    return runs


def _candidate_terms(text: str) -> tuple[dict[str, float], dict[str, str]]:
    """Score job-description terms, returning (key -> weight, key -> display)."""
    scores: dict[str, float] = {}
    surfaces: dict[str, dict[str, int]] = {}

    def record(key: str, surface: str, weight: float) -> None:
        scores[key] = scores.get(key, 0.0) + weight
        counts = surfaces.setdefault(key, {})
        counts[surface] = counts.get(surface, 0) + 1

    for line in text.split("\n"):
        lowered = line.lower()
        line_weight = 1.0
        if any(marker in lowered for marker in _REQUIREMENT_MARKERS):
            line_weight = 2.5
        elif re.match(r"^\s*[•\-\*]", line):
            line_weight = 1.6

        for tokens in _chunks(line):
            for token in tokens:
                if _is_noise(token):
                    continue
                record(_key(token), token, line_weight)
            for first, second in zip(tokens, tokens[1:]):
                if _is_noise(first) or _is_noise(second):
                    continue
                if len(first) < 3 or len(second) < 3:
                    continue
                record(_key(f"{first} {second}"), f"{first} {second}", line_weight * 1.4)

    display = {
        key: max(counts.items(), key=lambda kv: kv[1])[0] for key, counts in surfaces.items()
    }
    return scores, display


def _resume_vocabulary(text: str) -> set[str]:
    vocab: set[str] = set()
    for line in text.split("\n"):
        for tokens in _chunks(line):
            for token in tokens:
                vocab.add(token)
                vocab.add(_stem(token))
            for first, second in zip(tokens, tokens[1:]):
                vocab.add(f"{first} {second}")
                vocab.add(_key(f"{first} {second}"))
    return vocab


def _term_present(key: str, display: str, vocab: set[str]) -> tuple[bool, list[str]]:
    """Check the term and its known aliases against the resume vocabulary."""
    forms = {key, display, _key(display)}
    # "kubernetes" should match a resume that says "k8s", and vice versa.
    canonical = ALIAS_TO_CANONICAL.get(display, display)
    forms.add(canonical)
    forms.add(_key(canonical))
    for alias in SKILL_ALIASES.get(canonical, ()):
        forms.add(alias)
        forms.add(_key(alias))
    hits = sorted(f for f in forms if f and f in vocab)
    return bool(hits), hits


def build_keyword_report(ctx: ReviewContext, limit: int = 28) -> dict[str, object] | None:
    if not ctx.has_job_description:
        return None

    scores, display = _candidate_terms(ctx.job_description or "")
    if not scores:
        return None

    # Prefer multi-word terms slightly; they are more specific.
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], -len(kv[0].split()), kv[0]))

    # Drop a unigram when a higher-ranked bigram already covers it.
    chosen: list[tuple[str, float]] = []
    covered_words: set[str] = set()
    for key, weight in ranked:
        parts = key.split()
        if len(parts) == 1 and key in covered_words:
            continue
        chosen.append((key, weight))
        if len(parts) > 1:
            covered_words.update(parts)
        if len(chosen) >= limit:
            break

    vocab = _resume_vocabulary(ctx.text)
    matches: list[KeywordMatch] = []
    for key, weight in chosen:
        surface = display.get(key, key)
        present, variants = _term_present(key, surface, vocab)
        matches.append(
            KeywordMatch(term=surface, weight=weight, in_resume=present, variants=variants)
        )

    total_weight = sum(m.weight for m in matches) or 1.0
    matched_weight = sum(m.weight for m in matches if m.in_resume)
    coverage = matched_weight / total_weight

    return {
        "coverage": round(coverage, 4),
        "matched_count": sum(1 for m in matches if m.in_resume),
        "total_count": len(matches),
        "matched": [m.as_dict() for m in matches if m.in_resume],
        "missing": [m.as_dict() for m in matches if not m.in_resume],
    }


def check_keywords(ctx: ReviewContext) -> Iterator[Finding]:
    report = build_keyword_report(ctx)
    if report is None:
        return

    coverage: float = report["coverage"]  # type: ignore[assignment]
    missing: list[dict] = report["missing"]  # type: ignore[assignment]
    matched: list[dict] = report["matched"]  # type: ignore[assignment]
    top_missing = [m["term"] for m in missing[:8]]

    if coverage < 0.35:
        yield Finding(
            id="keywords.low_coverage",
            category=CAT, severity=Severity.CRITICAL,
            title=f"Only {coverage:.0%} of the job's key terms appear in your resume",
            detail=(
                f"{report['matched_count']} of {report['total_count']} weighted terms from "
                "the job description are evidenced here. At this level the application is "
                "unlikely to clear an automated screen, and a human reader won't see the fit either."
            ),
            fix=(
                "Work the genuinely applicable terms into your bullets, describing real "
                "work you did. Never list a skill you can't discuss in an interview."
            ),
            evidence=top_missing,
            penalty=45,
        )
    elif coverage < 0.6:
        yield Finding(
            id="keywords.partial_coverage",
            category=CAT, severity=Severity.WARNING,
            title=f"{coverage:.0%} coverage of the job's key terms",
            detail=(
                "A reasonable base, but several emphasised requirements have no supporting "
                "evidence in the resume."
            ),
            fix="Add the missing terms you can honestly evidence, ideally inside an achievement bullet.",
            evidence=top_missing,
            penalty=20,
        )
    else:
        yield Finding(
            id="keywords.strong_coverage",
            category=CAT, severity=Severity.POSITIVE,
            title=f"Strong match: {coverage:.0%} of key terms covered",
            detail="The resume already reflects most of what this job description emphasises.",
            evidence=[m["term"] for m in matched[:6]],
        )

    # Terms the JD leans on hardest deserve their own callout.
    critical_missing = [m for m in missing if m["weight"] >= 4.0][:5]
    if critical_missing:
        yield Finding(
            id="keywords.critical_missing",
            category=CAT, severity=Severity.WARNING,
            title="Heavily-emphasised requirements with no evidence",
            detail=(
                "These terms appear repeatedly in the job description, often on lines "
                "phrased as requirements, but nothing in the resume speaks to them."
            ),
            fix="For each one you can genuinely claim, add a bullet showing where you used it and what resulted.",
            evidence=[m["term"] for m in critical_missing],
            penalty=15,
        )

    # A skills section is where a tailored resume earns its coverage.
    if not ctx.has_section("skills") and missing:
        yield Finding(
            id="keywords.no_skills_section",
            category=CAT, severity=Severity.WARNING,
            title="No skills section to carry the job's terminology",
            detail=(
                "Without a skills section, matching depends entirely on your prose "
                "happening to use the same words as the job description."
            ),
            fix="Add a skills section listing the tools and methods this role names.",
            penalty=12,
        )
