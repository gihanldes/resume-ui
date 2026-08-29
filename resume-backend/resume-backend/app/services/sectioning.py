"""Split resume text into canonical sections.

Resumes have no schema, so headings are found by scoring each line on the
signals a human uses: it is short, it sits alone, it is styled like a heading
(caps / title case), and its words match a known section name.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from app.data.lexicon import SECTION_SYNONYMS

# Longest synonyms first so "work experience" wins over "experience".
_SYNONYM_INDEX: list[tuple[str, str]] = sorted(
    ((syn, canonical) for canonical, syns in SECTION_SYNONYMS.items() for syn in syns),
    key=lambda pair: len(pair[0]),
    reverse=True,
)

_HEADING_NOISE = re.compile(r"^[\s\W_]+|[\s\W_]+$")
_BULLET_LINE = re.compile(r"^\s*[•\-\*–—]\s+")
_MAX_HEADING_WORDS = 5
_MAX_HEADING_CHARS = 60


@dataclass
class Section:
    name: str           # canonical key, or "header" / "unknown"
    heading: str        # heading text as written ("" for the implicit header)
    start_line: int
    end_line: int       # exclusive
    lines: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.lines).strip()

    @property
    def word_count(self) -> int:
        return len(re.findall(r"\b[\w'-]+\b", self.text))


def _normalise_heading(line: str) -> str:
    stripped = _HEADING_NOISE.sub("", line)
    stripped = unicodedata.normalize("NFKC", stripped).lower()
    stripped = re.sub(r"\s+", " ", stripped)
    # "Work Experience & Projects" -> "work experience projects"
    stripped = re.sub(r"[&/]", " ", stripped)
    return re.sub(r"\s+", " ", stripped).strip()


def match_section_name(line: str) -> str | None:
    """Return the canonical section a heading line names, if any.

    Sentence fragments must not qualify: in multi-column PDFs, interleaved
    prose like "and technology transformation projects." would otherwise
    match a section synonym and shatter the document.
    """
    stripped = line.strip()
    if _BULLET_LINE.match(line):
        return None
    # Sentence punctuation at the end, or a lowercase start, means prose.
    if stripped.endswith((".", ",", ";")):
        return None
    first_alpha = next((ch for ch in stripped if ch.isalpha()), "")
    if first_alpha.islower():
        return None

    normalised = _normalise_heading(line)
    if not normalised or len(normalised.split()) > _MAX_HEADING_WORDS:
        return None
    for synonym, canonical in _SYNONYM_INDEX:
        if normalised == synonym:
            return canonical
    # Allow a trailing qualifier: "Technical Skills Summary".
    for synonym, canonical in _SYNONYM_INDEX:
        if normalised.startswith(f"{synonym} ") or normalised.endswith(f" {synonym}"):
            return canonical
    return None


def _heading_style(line: str) -> str | None:
    """Classify a line's heading style, or None if it isn't heading-shaped."""
    stripped = line.strip()
    if not stripped or len(stripped) > _MAX_HEADING_CHARS:
        return None
    if _BULLET_LINE.match(line):
        return None
    if stripped.endswith((".", ",", ";")):
        return None
    words = stripped.split()
    if not words or len(words) > _MAX_HEADING_WORDS:
        return None
    if not any(ch.isalpha() for ch in stripped):
        return None
    # Dates, contact details and pipe-separated meta lines are not headings.
    if re.search(r"\b(19|20)\d{2}\b", stripped) or "@" in stripped or "|" in stripped:
        return None

    if stripped.endswith(":"):
        return "colon"
    letters = [ch for ch in stripped if ch.isalpha()]
    if letters and sum(ch.isupper() for ch in letters) / len(letters) > 0.85:
        return "caps"
    if all(w[0].isupper() for w in words if w and w[0].isalpha()):
        return "title"
    return None


def _dominant_style(styles: list[str]) -> str | None:
    """The heading style this document actually uses for its named sections.

    Only returned when the style is *distinctive*. Title case is not: job titles
    and school names are title case too, so trusting it would split every role
    in the experience section into its own section.
    """
    if not styles:
        return None
    ranked = sorted({s: styles.count(s) for s in styles}.items(), key=lambda kv: -kv[1])
    top, count = ranked[0]
    if top in ("caps", "colon") and count >= 2:
        return top
    return None


def split_sections(text: str) -> list[Section]:
    """Split the resume into sections, in document order.

    Named headings ("Work Experience") always start a section. An unnamed line
    only starts one if it is styled exactly like this document's named headings,
    which keeps role titles inside the experience section where they belong.
    """
    lines = text.split("\n")

    # Pass 1 — headings we can name, and the style they are written in.
    named: list[tuple[int, str, str]] = []
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        canonical = match_section_name(stripped)
        if canonical:
            named.append((idx, canonical, stripped))

    dominant = _dominant_style([s for s in (_heading_style(h) for _, _, h in named) if s])

    # Pass 2 — assemble boundaries, adding unnamed headings only when they match.
    boundaries: list[tuple[int, str, str]] = list(named)
    if dominant:
        named_lines = {idx for idx, _, _ in named}
        for idx, line in enumerate(lines):
            if idx == 0 or idx in named_lines:
                continue  # line 0 is the candidate's name, never a section
            stripped = line.strip()
            if not stripped or not lines[idx - 1].strip():
                continue  # headings follow a blank line
            if _heading_style(stripped) == dominant:
                boundaries.append((idx, "unknown", stripped))
        boundaries.sort(key=lambda b: b[0])

    sections: list[Section] = []

    # Everything above the first heading is the contact header.
    first_boundary = boundaries[0][0] if boundaries else len(lines)
    if first_boundary > 0:
        sections.append(
            Section(
                name="header",
                heading="",
                start_line=0,
                end_line=first_boundary,
                lines=lines[0:first_boundary],
            )
        )

    for position, (line_idx, canonical, heading) in enumerate(boundaries):
        end = boundaries[position + 1][0] if position + 1 < len(boundaries) else len(lines)
        sections.append(
            Section(
                name=canonical,
                heading=heading,
                start_line=line_idx,
                end_line=end,
                lines=lines[line_idx + 1 : end],
            )
        )

    return sections


def sections_by_name(sections: list[Section]) -> dict[str, list[Section]]:
    grouped: dict[str, list[Section]] = {}
    for section in sections:
        grouped.setdefault(section.name, []).append(section)
    return grouped


def find_section(sections: list[Section], name: str) -> Section | None:
    """Return the largest section with this canonical name."""
    matches = [s for s in sections if s.name == name]
    if not matches:
        return None
    return max(matches, key=lambda s: s.word_count)
