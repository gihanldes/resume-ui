"""Rules covering how bullets are written: results versus responsibilities."""

from __future__ import annotations

import re
from collections.abc import Iterator

from app.data.lexicon import (
    ACTION_VERBS,
    ALL_ACTION_VERBS,
    CLICHE_PHRASES,
    FILLER_PHRASES,
    FIRST_PERSON_PRONOUNS,
    WEAK_OPENERS,
)
from app.services.parsing import Bullet
from app.services.rules.base import Category, Finding, ReviewContext, Severity

CAT = Category.IMPACT

# A bullet counts as quantified if it carries a number that means something:
# a percentage, money, a multiple, a scale, a count or a duration.
_QUANTIFIER_RE = re.compile(
    r"""
    (?:\d[\d,.]*\s?%)                                  # 43%
  | (?:[$£€¥₹]\s?\d[\d,.]*\s?(?:k|m|bn?|million|billion|thousand)?)  # $2.1B
  | (?:\b\d[\d,.]*\s?(?:k|m|bn|million|billion|thousand)\b)          # 250k
  | (?:\b\d+(?:\.\d+)?\s?x\b)                          # 3x
  | (?:\b\d[\d,.]*\s*(?:users?|customers?|clients?|people|engineers?|reports?|
        teams?|projects?|countries|markets|stores?|accounts?|tickets?|requests?|
        transactions?|records?|hours?|days?|weeks?|months?|years?|seconds?|ms))
  | (?:\b(?:from|to|by|over|under|within|across)\s+\d[\d,.]*)
  | (?:\b\d{2,}\b)                                     # any bare 2+ digit number
    """,
    re.IGNORECASE | re.VERBOSE,
)
# Years and dates are not achievements.
_DATE_LIKE_RE = re.compile(r"\b(19|20)\d{2}\b")

_PAST_TENSE_RE = re.compile(r"\b\w+ed\b")
_PRESENT_ING_RE = re.compile(r"\b\w+ing\b")

_LONG_BULLET_WORDS = 34
_SHORT_BULLET_WORDS = 6


def _is_quantified(bullet: Bullet) -> bool:
    text = _DATE_LIKE_RE.sub(" ", bullet.text)
    return bool(_QUANTIFIER_RE.search(text))


def _suggest_verb(bullet: Bullet) -> str:
    """Pick a plausible strong verb for a weak bullet, by topic."""
    low = bullet.text.lower()
    if any(w in low for w in ("team", "junior", "mentor", "manage", "stakeholder")):
        group = "leadership"
    elif any(w in low for w in ("cost", "time", "latency", "performance", "speed", "efficien")):
        group = "improvement"
    elif any(w in low for w in ("build", "develop", "design", "create", "app", "feature", "system")):
        group = "creation"
    elif any(w in low for w in ("report", "data", "analys", "analyz", "research", "metric")):
        group = "analysis"
    else:
        group = "achievement"
    return ", ".join(sorted(ACTION_VERBS[group])[:4])


def check_impact(ctx: ReviewContext) -> Iterator[Finding]:
    bullets = ctx.experience_bullets

    # --- no bullets at all --------------------------------------------------
    if not bullets:
        yield Finding(
            id="impact.no_bullets",
            category=CAT, severity=Severity.CRITICAL,
            title="Experience isn't written as bullet points",
            detail=(
                "No bullet points were found under your roles. Dense paragraphs are "
                "skimmed and abandoned. A recruiter spends roughly six to eight seconds "
                "on a first pass, and prose does not survive that."
            ),
            fix="Rewrite each role as 3-5 bullets, one achievement per bullet.",
            penalty=45,
        )
        return

    total = len(bullets)

    # --- quantified achievements -------------------------------------------
    quantified = [b for b in bullets if _is_quantified(b)]
    ratio = len(quantified) / total
    unquantified = [b for b in bullets if b not in quantified]

    if ratio < 0.20:
        yield Finding(
            id="impact.no_metrics",
            category=CAT, severity=Severity.CRITICAL,
            title=f"Only {len(quantified)} of {total} bullets contain a number",
            detail=(
                "Almost nothing here is measurable. 'Improved the checkout flow' and "
                "'Improved checkout conversion by 18%, worth £240k a year' describe the "
                "same work, but only one gives an interviewer something to ask about."
            ),
            fix=(
                "Add a number to at least half your bullets: percentage change, money, "
                "volume, team size, or time saved. Estimate where you must. A defensible "
                "approximation beats nothing."
            ),
            evidence=[b.text for b in unquantified[:3]],
            penalty=32,
        )
    elif ratio < 0.45:
        yield Finding(
            id="impact.few_metrics",
            category=CAT, severity=Severity.WARNING,
            title=f"Only {ratio:.0%} of bullets are quantified",
            detail=(
                f"{len(quantified)} of {total} bullets carry a number. The unquantified "
                "ones read as job description rather than track record."
            ),
            fix="Aim for a number in roughly half your bullets, concentrated in your most recent role.",
            evidence=[b.text for b in unquantified[:3]],
            penalty=16,
        )
    elif ratio >= 0.6:
        yield Finding(
            id="impact.well_quantified",
            category=CAT, severity=Severity.POSITIVE,
            title=f"{ratio:.0%} of bullets are quantified",
            detail="Most bullets carry a concrete number, which is exactly what a hiring manager screens for.",
            evidence=[b.text for b in quantified[:2]],
        )

    # --- weak openers -------------------------------------------------------
    weak = [b for b in bullets if b.first_word in WEAK_OPENERS]
    if weak:
        share = len(weak) / total
        severity = Severity.CRITICAL if share > 0.4 else Severity.WARNING
        yield Finding(
            id="impact.weak_openers",
            category=CAT, severity=severity,
            title=f"{len(weak)} bullet(s) open with a weak verb",
            detail=(
                "Openers like 'Responsible for', 'Worked on' and 'Helped with' describe "
                "a job description, not what you personally achieved. The first word of "
                "a bullet is the one most likely to be read."
            ),
            fix=f"Start with a strong past-tense verb instead, for example: {_suggest_verb(weak[0])}.",
            evidence=[b.text for b in weak[:4]],
            penalty=min(26.0, 7.0 * len(weak)),
        )

    # --- strong verb coverage ----------------------------------------------
    strong = [b for b in bullets if b.first_word in ALL_ACTION_VERBS]
    if not weak and len(strong) / total >= 0.7:
        yield Finding(
            id="impact.strong_verbs",
            category=CAT, severity=Severity.POSITIVE,
            title="Bullets lead with strong action verbs",
            detail="Nearly every bullet opens on an action, which keeps the writing direct.",
        )
    elif len(strong) / total < 0.4 and not weak:
        yield Finding(
            id="impact.few_action_verbs",
            category=CAT, severity=Severity.WARNING,
            title="Most bullets don't start with an action verb",
            detail=(
                f"Only {len(strong)} of {total} bullets open on a recognised action verb. "
                "Bullets that begin with a noun or an article read as descriptions of a "
                "situation rather than of something you did."
            ),
            fix="Restructure each bullet as: strong verb -> what you did -> measurable result.",
            evidence=[b.text for b in bullets if b.first_word not in ALL_ACTION_VERBS][:3],
            penalty=14,
        )

    # --- repeated verbs -----------------------------------------------------
    openers: dict[str, int] = {}
    for bullet in bullets:
        if bullet.first_word:
            openers[bullet.first_word] = openers.get(bullet.first_word, 0) + 1
    overused = [(verb, n) for verb, n in openers.items() if n >= 4 and total >= 6]
    if overused:
        verb, count = max(overused, key=lambda pair: pair[1])
        yield Finding(
            id="impact.repeated_verbs",
            category=CAT, severity=Severity.SUGGESTION,
            title=f"'{verb.title()}' opens {count} different bullets",
            detail="Repeating the same opener flattens the writing and makes distinct achievements blur together.",
            fix="Vary the verb to match what each bullet actually did: built, scaled, negotiated, reduced.",
            penalty=5,
        )

    # --- filler and clichés -------------------------------------------------
    lowered = ctx.flat_text
    fillers = [p for p in FILLER_PHRASES if p in lowered]
    if fillers:
        yield Finding(
            id="impact.filler_phrases",
            category=CAT, severity=Severity.WARNING,
            title=f"{len(fillers)} filler phrase(s) found",
            detail=(
                "Phrases like these add words without adding information, and they push "
                "the substance further down the line."
            ),
            fix="Delete the phrase and start the sentence at the verb.",
            evidence=fillers[:5],
            penalty=min(14.0, 3.5 * len(fillers)),
        )

    cliches = [p for p in CLICHE_PHRASES if p in lowered]
    if cliches:
        yield Finding(
            id="impact.cliches",
            category=CAT, severity=Severity.WARNING,
            title=f"{len(cliches)} unsupported self-description(s)",
            detail=(
                "Claims like 'team player' and 'proven track record' assert a quality "
                "without evidencing it. Every candidate writes them, so they carry no "
                "signal. The evidence has to be the achievement itself."
            ),
            fix="Delete the claim and replace it with the achievement that demonstrates it.",
            evidence=cliches[:5],
            penalty=min(16.0, 4.0 * len(cliches)),
        )

    # --- first person -------------------------------------------------------
    pronouns = [
        w for w in re.findall(r"\b[\w']+\b", lowered) if w in FIRST_PERSON_PRONOUNS
    ]
    if len(pronouns) >= 3:
        yield Finding(
            id="impact.first_person",
            category=CAT, severity=Severity.SUGGESTION,
            title=f"First-person pronouns used {len(pronouns)} times",
            detail=(
                "Resumes are conventionally written in an implied first person with the "
                "pronoun dropped: 'Led the migration', not 'I led the migration'."
            ),
            fix="Remove I / me / my / we and start directly from the verb.",
            evidence=sorted(set(pronouns))[:5],
            penalty=7,
        )

    # --- bullet length ------------------------------------------------------
    long_bullets = [b for b in bullets if b.word_count > _LONG_BULLET_WORDS]
    if len(long_bullets) >= max(2, total * 0.25):
        yield Finding(
            id="impact.bullets_too_long",
            category=CAT, severity=Severity.WARNING,
            title=f"{len(long_bullets)} bullet(s) run over {_LONG_BULLET_WORDS} words",
            detail=(
                "Long bullets are scanned, not read. Anything past roughly two lines "
                "tends to be skipped entirely, including the result at the end."
            ),
            fix="Cut each to one or two lines. Lead with the outcome, then the method.",
            evidence=[b.text for b in long_bullets[:3]],
            penalty=10,
        )

    stub_bullets = [b for b in bullets if b.word_count < _SHORT_BULLET_WORDS]
    if len(stub_bullets) >= max(2, total * 0.3):
        yield Finding(
            id="impact.bullets_too_short",
            category=CAT, severity=Severity.SUGGESTION,
            title=f"{len(stub_bullets)} bullet(s) are only a few words",
            detail="Very short bullets tend to name a technology or a duty without any outcome.",
            fix="Expand each into an achievement: what you did, and what changed as a result.",
            evidence=[b.text for b in stub_bullets[:3]],
            penalty=7,
        )

    # --- tense consistency in the current role -----------------------------
    current_bullets = [b for b in bullets if b.section == "experience"][:6]
    if len(current_bullets) >= 4:
        past = sum(bool(_PAST_TENSE_RE.search(b.text)) for b in current_bullets)
        gerund = sum(bool(_PRESENT_ING_RE.match(b.text.split()[0])) for b in current_bullets if b.text.split())
        if past and gerund and abs(past - gerund) < len(current_bullets) * 0.5:
            yield Finding(
                id="impact.mixed_tense",
                category=CAT, severity=Severity.SUGGESTION,
                title="Verb tense is inconsistent between bullets",
                detail=(
                    "Some bullets are past tense and others are present participles. "
                    "Convention is present tense for your current role and past tense "
                    "for everything before it, applied consistently within each role."
                ),
                fix="Pick one tense per role and apply it to every bullet in that role.",
                penalty=5,
            )
