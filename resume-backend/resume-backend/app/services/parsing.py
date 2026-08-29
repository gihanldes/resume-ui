"""Pull structured facts out of resume text: contact details, bullets, dates."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from app.services.sectioning import Section, find_section

# --------------------------------------------------------------------------- #
# Contact details
# --------------------------------------------------------------------------- #
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
# Deliberately permissive: international formats vary wildly.
PHONE_RE = re.compile(
    r"(?<![\w.])(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)[\s.-]?|\d{2,4}[\s.-])?"
    r"\d{3}[\s.-]?\d{3,4}(?:[\s.-]?\d{2,4})?(?![\w])"
)
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/(?:in|pub)/[\w\-%.]+", re.I)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[\w\-.]+", re.I)
URL_RE = re.compile(r"(?:https?://|www\.)[\w\-.]+\.[a-z]{2,}(?:/[\w\-./?%&=+#]*)?", re.I)
# "San Francisco, CA" / "Berlin, Germany" / "London, UK".
# Uses [ \t] rather than \s so a match can never span two lines.
LOCATION_RE = re.compile(
    r"\b([A-Z][a-zA-Z.'-]+(?:[ \t]+[A-Z][a-zA-Z.'-]+){0,2}),[ \t]*([A-Z]{2,3}|[A-Z][a-z]+)\b"
)

PHOTO_HINTS = ("photo", "photograph", "picture", "headshot")
SENSITIVE_FIELDS = (
    "date of birth", "dob", "birthdate", "birth date", "marital status",
    "nationality", "gender", "religion", "age:", "passport", "social security",
    "ssn", "civil status",
)


@dataclass
class ContactInfo:
    name: str | None = None
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    linkedin: str | None = None
    github: str | None = None
    websites: list[str] = field(default_factory=list)
    location: str | None = None
    sensitive_fields: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "emails": self.emails,
            "phones": self.phones,
            "linkedin": self.linkedin,
            "github": self.github,
            "websites": self.websites,
            "location": self.location,
            "sensitive_fields": self.sensitive_fields,
        }


def _looks_like_name(line: str) -> bool:
    stripped = line.strip()
    if not (2 <= len(stripped.split()) <= 5) or len(stripped) > 60:
        return False
    if any(ch.isdigit() for ch in stripped) or "@" in stripped or "|" in stripped:
        return False
    words = [w for w in re.split(r"[\s,]+", stripped) if w]
    alpha = [w for w in words if any(ch.isalpha() for ch in w)]
    if not alpha:
        return False
    return all(w[0].isupper() for w in alpha if w[0].isalpha())


def extract_contact(text: str, sections: list[Section]) -> ContactInfo:
    header = find_section(sections, "header")
    header_text = header.text if header else "\n".join(text.split("\n")[:8])
    info = ContactInfo()

    for line in header_text.split("\n"):
        if _looks_like_name(line):
            info.name = line.strip()
            break

    # Contact details usually live in the header, but tolerate a footer layout.
    scope = header_text if EMAIL_RE.search(header_text) else text

    info.emails = list(dict.fromkeys(EMAIL_RE.findall(scope)))

    phone_scope = scope
    for email in info.emails:
        phone_scope = phone_scope.replace(email, " ")
    phone_scope = URL_RE.sub(" ", phone_scope)
    for raw in PHONE_RE.findall(phone_scope):
        digits = re.sub(r"\D", "", raw)
        if 7 <= len(digits) <= 15 and raw.strip() not in info.phones:
            info.phones.append(raw.strip())

    if match := LINKEDIN_RE.search(text):
        info.linkedin = match.group(0)
    if match := GITHUB_RE.search(text):
        info.github = match.group(0)

    for url in URL_RE.findall(scope):
        low = url.lower()
        if "linkedin.com" in low or "github.com" in low:
            continue
        if url not in info.websites:
            info.websites.append(url)

    # Search line by line, skipping the name line, so the surname can't be
    # mistaken for a city.
    for line in header_text.split("\n"):
        if info.name and line.strip() == info.name:
            continue
        if match := LOCATION_RE.search(line):
            info.location = match.group(0).strip()
            break

    # Collapse whitespace so a phrase split across a PDF line break still matches.
    lowered = re.sub(r"\s+", " ", text.lower())
    info.sensitive_fields = [f for f in SENSITIVE_FIELDS if f in lowered]
    if any(hint in lowered for hint in PHOTO_HINTS):
        info.sensitive_fields.append("photo reference")

    return info


# --------------------------------------------------------------------------- #
# Bullets
# --------------------------------------------------------------------------- #
BULLET_RE = re.compile(r"^\s*[•\-\*‣▪◦]\s+(?P<body>.+)$")


@dataclass
class Bullet:
    text: str
    line_index: int
    section: str

    @property
    def words(self) -> list[str]:
        return re.findall(r"\b[\w'-]+\b", self.text)

    @property
    def word_count(self) -> int:
        return len(self.words)

    @property
    def first_word(self) -> str:
        return self.words[0].lower() if self.words else ""


def extract_bullets(sections: list[Section]) -> list[Bullet]:
    bullets: list[Bullet] = []
    for section in sections:
        for offset, line in enumerate(section.lines):
            if match := BULLET_RE.match(line):
                body = match.group("body").strip()
                if len(body) > 3:
                    bullets.append(
                        Bullet(
                            text=body,
                            line_index=section.start_line + 1 + offset,
                            section=section.name,
                        )
                    )
    return bullets


# --------------------------------------------------------------------------- #
# Dates and employment timeline
# --------------------------------------------------------------------------- #
MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
    "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_MONTH_ALT = "|".join(sorted(MONTHS, key=len, reverse=True))
PRESENT_RE = re.compile(r"\b(present|current|now|to date|ongoing)\b", re.I)

_DATE_TOKEN = rf"(?:(?:{_MONTH_ALT})\.?\s+)?(?:\d{{1,2}}[/.-])?(?:19|20)\d{{2}}"
DATE_RANGE_RE = re.compile(
    rf"(?P<start>{_DATE_TOKEN})\s*(?:-|–|—|to|until|through)\s*"
    rf"(?P<end>{_DATE_TOKEN}|present|current|now|ongoing|to date)",
    re.I,
)
YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


@dataclass
class DateRange:
    raw: str
    start_year: int
    start_month: int | None
    end_year: int | None      # None means "present"
    end_month: int | None
    is_current: bool
    line_index: int
    section: str = ""

    @property
    def start_ordinal(self) -> int:
        return self.start_year * 12 + (self.start_month or 1)

    def end_ordinal(self, today: date) -> int:
        if self.is_current or self.end_year is None:
            return today.year * 12 + today.month
        return self.end_year * 12 + (self.end_month or 12)

    def as_dict(self) -> dict[str, object]:
        return {
            "raw": self.raw,
            "start_year": self.start_year,
            "start_month": self.start_month,
            "end_year": self.end_year,
            "end_month": self.end_month,
            "is_current": self.is_current,
            "section": self.section,
        }


def _parse_date_token(token: str) -> tuple[int, int | None] | None:
    token = token.strip().lower().rstrip(".")
    year_match = YEAR_RE.search(token)
    if not year_match:
        return None
    year = int(year_match.group(0))
    month: int | None = None
    for name, number in MONTHS.items():
        if re.search(rf"\b{name}\b", token):
            month = number
            break
    if month is None:
        if numeric := re.match(r"^(\d{1,2})[/.-]", token):
            candidate = int(numeric.group(1))
            if 1 <= candidate <= 12:
                month = candidate
    return year, month


def extract_date_ranges(text: str) -> list[DateRange]:
    ranges: list[DateRange] = []
    for line_index, line in enumerate(text.split("\n")):
        for match in DATE_RANGE_RE.finditer(line):
            start = _parse_date_token(match.group("start"))
            if not start:
                continue
            end_raw = match.group("end")
            is_current = bool(PRESENT_RE.fullmatch(end_raw.strip()))
            end = None if is_current else _parse_date_token(end_raw)
            ranges.append(
                DateRange(
                    raw=match.group(0).strip(),
                    start_year=start[0],
                    start_month=start[1],
                    end_year=end[0] if end else None,
                    end_month=end[1] if end else None,
                    is_current=is_current,
                    line_index=line_index,
                )
            )
    return ranges


def assign_sections(ranges: list[DateRange], sections: list[Section]) -> list[DateRange]:
    """Tag each date range with the section it was found in.

    Education dates must not be counted as employment, so tenure and gap
    calculations can filter on this.
    """
    for date_range in ranges:
        for section in sections:
            if section.start_line <= date_range.line_index < section.end_line:
                date_range.section = section.name
                break
    return ranges


@dataclass
class TimelineGap:
    after_year: int
    after_month: int
    before_year: int
    before_month: int
    months: int

    def as_dict(self) -> dict[str, object]:
        return {
            "from": f"{self.after_year}-{self.after_month:02d}",
            "to": f"{self.before_year}-{self.before_month:02d}",
            "months": self.months,
        }


def find_gaps(ranges: list[DateRange], today: date, min_months: int = 6) -> list[TimelineGap]:
    """Gaps between consecutive roles, ignoring overlaps."""
    if len(ranges) < 2:
        return []
    spans = sorted(
        ((r.start_ordinal, r.end_ordinal(today)) for r in ranges), key=lambda s: s[0]
    )
    gaps: list[TimelineGap] = []
    covered_until = spans[0][1]
    for start, end in spans[1:]:
        gap_months = start - covered_until
        if gap_months >= min_months:
            gaps.append(
                TimelineGap(
                    after_year=covered_until // 12,
                    after_month=max(1, covered_until % 12 or 12),
                    before_year=start // 12,
                    before_month=max(1, start % 12 or 12),
                    months=gap_months,
                )
            )
        covered_until = max(covered_until, end)
    return gaps


def total_experience_months(ranges: list[DateRange], today: date) -> int:
    """Union of all employment spans, so overlapping roles aren't double counted."""
    if not ranges:
        return 0
    spans = sorted(((r.start_ordinal, r.end_ordinal(today)) for r in ranges), key=lambda s: s[0])
    merged: list[list[int]] = [list(spans[0])]
    for start, end in spans[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return sum(max(0, end - start) for start, end in merged)
