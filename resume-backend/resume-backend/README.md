# Resume Reviewer — API

FastAPI, async SQLAlchemy, JWT auth with refresh-token rotation.

## Setup

```bash
cp .env.example .env
.venv/bin/python -m pip install -r requirements.txt
./run.sh
```

Interactive docs at http://127.0.0.1:8000/docs.

`SECRET_KEY` is required when `ENVIRONMENT=production` and must be at least 32
bytes. In development an ephemeral key is generated at startup, which means
tokens are invalidated whenever the server restarts.

## Layout

```
app/
  main.py            app factory, CORS, validation-error shaping
  config.py          settings (pydantic-settings)
  db.py              async engine + session dependency
  models.py          User, RefreshToken, Resume, Analysis
  schemas.py         request/response models
  security.py        argon2 hashing, JWT issue/decode
  deps.py            get_current_user
  api/               auth, resumes, analyses, health
  services/
    extraction.py    PDF/DOCX/TXT -> text + layout signals
    sectioning.py    heading detection and section splitting
    parsing.py       contact details, bullets, date ranges, gaps
    analyzer.py      orchestration: parse once, run rules, score
    scoring.py       category budgets -> overall score
    ai_review.py     optional OpenAI layer
    rules/           one module per category
  data/lexicon.py    action verbs, filler, clichés, section synonyms, stopwords
```

## Endpoints beyond CRUD

- `GET /api/analyses/{id}/compare[?with=]` — score deltas per category plus
  findings resolved/introduced. Without `?with=` the baseline is the most
  recent earlier review of the same resume, falling back to any earlier review
  (a revision is usually re-uploaded as a new file).
- `POST /api/analyses/{id}/ai` — add or retry the AI layer on an existing
  analysis. 503 with a plain explanation when no key is configured.
- `DELETE /api/auth/me` — password-confirmed account deletion; cascades to all
  resumes, analyses and sessions.

## Hardening

- Rate limits (settings-tunable): auth 10/min per IP; uploads 15/min and
  analyses 6/min per user. In-memory sliding windows — single process only;
  use Redis if you scale out workers. 429 responses carry `Retry-After`.
- Middleware adds `X-Request-ID`, nosniff/frame-deny/no-referrer headers,
  `Cache-Control: no-store` on API paths, and rejects bodies over 12 MB before
  reading them. Uploads are additionally read with a hard cap.

## Design notes

**Extraction captures layout, not just text.** Multi-column detection,
table counts, images and header/footer text all feed the ATS rules — none of
that is visible in the extracted string, and it is the main reason resumes get
mis-parsed.

**Section splitting infers the document's own heading style.** Named headings
("Work Experience") always start a section. An unnamed line only starts one if
it matches the style the named headings use, and only when that style is
distinctive (all-caps or trailing colon). Title case is never trusted, because
job titles and school names are title case too — trusting it would split every
role in the experience section into its own section.

**Date ranges are tagged with their section**, so an education date can never
be counted as employment tenure.

**Phrase matching runs against whitespace-collapsed text.** PDFs hard-wrap
lines, so "proven track record" is frequently split across a newline.

**Keyword matching stems both sides consistently** and never forms a bigram
across punctuation — "PostgreSQL, Kafka" is two skills, not one term called
"postgresql kafka". Job-description boilerplate ("require", "expertise",
"familiar") is excluded so it is never presented as a missing skill.

**One failing rule cannot fail the review.** Rule exceptions are collected into
`rule_errors` and the remaining categories still score.

## Auth

- Argon2id password hashing, with transparent rehash on login when parameters change.
- Short-lived access tokens; refresh tokens are stored only as SHA-256 digests.
- Refresh tokens are single-use. Replaying a spent one revokes every session for
  that user, on the assumption the token leaked.
- Login runs a password verification even for unknown emails, so response timing
  does not reveal whether an account exists.
