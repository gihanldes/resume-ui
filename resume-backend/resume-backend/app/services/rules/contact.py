"""Rules covering the header block: can a recruiter identify and reach you?"""

from __future__ import annotations

import re
from collections.abc import Iterator

from app.services.rules.base import Category, Finding, ReviewContext, Severity

_UNPROFESSIONAL_LOCAL = re.compile(
    r"^(sexy|hot|babe|cute|crazy|lazy|killer|gangsta|dude|princess|beast|savage)"
    r"|(69|420|666|xoxo|lol|omg)", re.I
)
_DATED_DOMAINS = {"aol.com", "hotmail.com", "yahoo.com", "live.com", "msn.com"}
CAT = Category.CONTACT


def check_contact(ctx: ReviewContext) -> Iterator[Finding]:
    contact = ctx.contact

    # --- name ---------------------------------------------------------------
    if not contact.name:
        yield Finding(
            id="contact.name_missing",
            category=CAT, severity=Severity.CRITICAL,
            title="No clear name at the top",
            detail=(
                "The first lines of the document don't contain something that reads "
                "as your full name. Parsers use the top line to populate the "
                "candidate record, and recruiters skim it first."
            ),
            fix="Put your full name alone on the first line, in the largest text on the page.",
            penalty=25,
        )

    # --- email --------------------------------------------------------------
    if not contact.emails:
        yield Finding(
            id="contact.email_missing",
            category=CAT, severity=Severity.CRITICAL,
            title="No email address found",
            detail=(
                "No email address could be read from the resume. This is the single "
                "most common way a recruiter replies, and an application without one "
                "is usually discarded outright."
            ),
            fix="Add a professional email address to the header, as plain selectable text.",
            penalty=40,
        )
    else:
        primary = contact.emails[0]
        local, _, domain = primary.partition("@")
        if _UNPROFESSIONAL_LOCAL.search(local):
            yield Finding(
                id="contact.email_unprofessional",
                category=CAT, severity=Severity.WARNING,
                title="Email address reads as informal",
                detail=(
                    f"'{primary}' is likely to read as unprofessional to a hiring manager, "
                    "regardless of the rest of the resume."
                ),
                fix="Use an address built from your name, e.g. firstname.lastname@gmail.com.",
                evidence=[primary],
                penalty=15,
            )
        elif domain.lower() in _DATED_DOMAINS:
            yield Finding(
                id="contact.email_dated_domain",
                category=CAT, severity=Severity.SUGGESTION,
                title="Email provider looks dated",
                detail=(
                    f"'{domain}' can read as out of date in some markets. This is cosmetic, "
                    "but it is a free signal to fix."
                ),
                fix="Consider a Gmail, Outlook or personal-domain address.",
                evidence=[primary],
                penalty=4,
            )
        if len(contact.emails) > 1:
            yield Finding(
                id="contact.email_multiple",
                category=CAT, severity=Severity.SUGGESTION,
                title="More than one email address listed",
                detail="Multiple addresses make it ambiguous where a reply should go.",
                fix="Keep a single preferred email address.",
                evidence=contact.emails[:3],
                penalty=5,
            )

    # --- phone --------------------------------------------------------------
    if not contact.phones:
        yield Finding(
            id="contact.phone_missing",
            category=CAT, severity=Severity.WARNING,
            title="No phone number found",
            detail=(
                "Recruiters often call before they email, especially for a first screen. "
                "No readable phone number was found."
            ),
            fix="Add a phone number in international format, e.g. +1 415 555 0142.",
            penalty=15,
        )

    # --- links --------------------------------------------------------------
    if not contact.linkedin:
        yield Finding(
            id="contact.linkedin_missing",
            category=CAT, severity=Severity.SUGGESTION,
            title="No LinkedIn profile linked",
            detail=(
                "Most recruiters check LinkedIn before responding. Omitting it makes them "
                "search for you, and they may find the wrong person."
            ),
            fix="Add your public profile URL, e.g. linkedin.com/in/yourname.",
            penalty=8,
        )

    has_portfolio = bool(contact.github or contact.websites)
    if not has_portfolio:
        yield Finding(
            id="contact.portfolio_missing",
            category=CAT, severity=Severity.SUGGESTION,
            title="No portfolio, GitHub or personal site",
            detail=(
                "For technical and creative roles, a link to work samples is one of the "
                "strongest differentiators on a resume."
            ),
            fix="Add a GitHub, portfolio or personal-site URL if you have relevant work to show.",
            penalty=5,
        )

    # --- location -----------------------------------------------------------
    if not contact.location:
        yield Finding(
            id="contact.location_missing",
            category=CAT, severity=Severity.SUGGESTION,
            title="No location given",
            detail=(
                "Recruiters filter by location for visa, time-zone and hybrid-policy "
                "reasons. A missing location can get an application skipped."
            ),
            fix="Add city and country (or 'Remote, based in <city>'). A full street address is not needed.",
            penalty=6,
        )

    # --- privacy ------------------------------------------------------------
    if contact.sensitive_fields:
        yield Finding(
            id="contact.sensitive_data",
            category=CAT, severity=Severity.WARNING,
            title="Personal details that don't belong on a resume",
            detail=(
                "The resume appears to include personal data that is not job-relevant "
                f"({', '.join(contact.sensitive_fields[:4])}). In the US, UK and much of "
                "the EU, employers actively avoid resumes carrying it, because it creates "
                "discrimination-claim exposure for them."
            ),
            fix="Remove date of birth, marital status, gender, nationality and photo unless the local market expects them.",
            evidence=contact.sensitive_fields[:4],
            penalty=18,
        )

    # --- positives ----------------------------------------------------------
    if contact.emails and contact.phones and contact.linkedin:
        yield Finding(
            id="contact.complete",
            category=CAT, severity=Severity.POSITIVE,
            title="Contact details are complete",
            detail="Name, email, phone and LinkedIn are all present and machine-readable.",
        )
