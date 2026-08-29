# Proof: resume review

Proof is an AI resume reviewer. It validates a resume against a target role
and job description with a language-model critique, grounded in a
deterministic score where every deduction names the exact words that caused
it, so the feedback is both intelligent and auditable.

**Live application:** https://proof-1085004910130.us-central1.run.app

---

## 1. Problem Statement

Most resumes are screened by software before a person ever reads them.
Candidates get rejected without knowing why: the parser could not read a
two-column layout, the bullets carry no measurable impact, or the resume
simply never mentions the keywords the posting asked for. Existing "AI resume
checkers" make this worse by returning a vague grade with no evidence, so the
candidate cannot tell what to change or whether a change helped.

The problem Proof addresses: give a job seeker a score they can audit, tied to
the exact text that caused each deduction, and a clear ranking of what to fix
first.

## 2. Use Case

- A job seeker uploads their resume before applying and fixes the highest
  value issues first, guided by per-finding point gains.
- A candidate targeting one specific posting pastes the job description and
  gets weighted keyword coverage against it.
- Someone iterating on their resume re-runs the review after each edit; the
  app tracks the score across runs, shows the delta against the previous
  review, and charts progress over time.
- Any review exports as a print-ready report.

It is a general-purpose web application: anyone can create an account at the
live URL, and the same build can be self-hosted by anyone with the repo.

## 3. Solution Overview

Each uploaded resume goes through an AI-assisted validation pipeline:

1. **Extraction**: the PDF, DOCX or text file is parsed in memory into plain
   text plus layout signals (columns, tables, images), the same view an
   applicant tracking system gets.
2. **AI resume validation**: the language model reads the extracted resume
   together with the candidate's target role and, when supplied, the full job
   description, and evaluates it the way a human screener would.
3. **Deterministic scoring**: in parallel, a rule engine computes the numeric
   score so every point on screen is reproducible and auditable.

The AI validation covers six dimensions:

| AI validation | What the model evaluates |
|---|---|
| Overall impression | A recruiter-style read of how the resume lands for the target role |
| Estimated level | The seniority the resume actually signals, compared with the role being targeted |
| Strengths | What genuinely works and should be kept as is |
| Red flags | Unsupported claims, gaps and inconsistencies a screener would question |
| Priority actions | A ranked list of what to fix first for the biggest improvement |
| Bullet rewrites | Weak bullets rewritten in stronger form, with `[X%]` placeholders where a real number belongs, because the model is forbidden to invent metrics |

The numeric score underneath comes from the deterministic engine: six weighted
categories (contact and header, structure, impact and writing, ATS
compatibility, formatting and length, job match), each a 100-point budget that
findings deduct from, with every deduction naming the exact words that caused
it. This split is deliberate: the AI provides the judgement and the writing,
the engine guarantees the numbers are honest and repeatable. If no OpenAI key
is configured the app degrades gracefully to the scored review alone and says
why the AI section is absent.

## 4. Dataset

No training dataset is used and no model is trained in this project. Two data
artifacts exist:

- **Curated lexicons** ([app/data/lexicon.py](resume-backend/resume-backend/app/data/lexicon.py)):
  hand-built word lists that power the deterministic rules, including strong
  action verbs grouped by theme (leadership, achievement, improvement,
  creation), weak openers, filler phrases, cliches, and unsupported
  self-description terms. Kept as plain Python so the rules are importable
  without I/O and easy to extend.
- **User uploads at runtime**: resumes uploaded by account holders. The
  original file is parsed in memory and discarded; only the extracted text is
  stored, scoped to the owning account, and deleted permanently when the user
  deletes the resume or the account. User data is never used for training and
  never shared between accounts.

## 5. AI/ML Approach

- **Model:** OpenAI `gpt-5-mini`, called through the official `openai` Python
  SDK. No fine-tuning; the value is in prompt design and strict output rules.
- **Prompting:** the extracted resume text (capped at 24,000 characters to
  bound cost), the target role, and the job description when given, with
  instructions that fix the output structure (overall impression, strengths,
  red flags, priority actions, bullet rewrites, estimated level) and forbid
  invented numbers and em-dash or arrow styled prose.
- **Guardrails:** a 90 second timeout, a 4,000 token output cap, graceful
  degradation (an AI failure is recorded on the analysis and shown honestly,
  never blocking the deterministic result), and a per-user rate limit on
  analysis runs.
- **Deliberately not ML:** the score itself. The rule engine
  ([app/services/rules/](resume-backend/resume-backend/app/services/rules/))
  is explainable by construction, which is the product's differentiator; the
  LLM handles only the qualitative language a rule engine cannot write.
- **Supporting libraries:** `pypdf` and `pdfplumber` for PDF text and layout
  signals, `python-docx` for DOCX, plus custom sectioning and parsing in
  [app/services/](resume-backend/resume-backend/app/services/).

## 6. Application Architecture

One container serves everything; the only external dependencies are the
database and the OpenAI API.

```
Browser (React SPA)
│  same origin, /api/*
Cloud Run service "proof"  (one container, max 1 instance, scales to zero)
├─ FastAPI app
│   ├─ serves the built React bundle (SPA fallback, traversal-guarded)
│   ├─ REST API under /api (JWT auth, rate limiting, security headers)
│   ├─ extraction: PDF/DOCX/TXT to text plus layout signals
│   ├─ rule engine: six categories, deterministic score (engine v1.2)
│   └─ AI review client (OpenAI gpt-5-mini, optional)
├─ Cloud SQL connector (unix socket)
│   └─ Cloud SQL: Postgres 17 (users, sessions, resumes, analyses)
└─ Secret Manager: SECRET_KEY, OPENAI_API_KEY, DATABASE_URL
```

Auth is full-account JWT: short-lived access tokens plus single-use refresh
tokens with rotation and reuse detection (replaying a spent token revokes
every session for that user). Uploaded files are never stored; only extracted
text is. Passwords are argon2 hashes; refresh tokens are stored only as
SHA-256 hashes.

## 7. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript, Vite 8, Tailwind CSS v4 |
| Backend | Python 3.14, FastAPI, SQLAlchemy 2 (async), Pydantic v2, Uvicorn |
| Database | PostgreSQL 17 on Cloud SQL (production), SQLite via aiosqlite (dev/tests) |
| Auth | PyJWT, argon2-cffi |
| Document parsing | pypdf, pdfplumber, python-docx |
| AI | OpenAI API (gpt-5-mini) |
| Cloud (GCP) | Cloud Run, Cloud SQL, Artifact Registry, Secret Manager |
| Packaging | Docker (multi-stage: Node build, Python runtime) |
| Tests | pytest, httpx |

## 8. Local Setup Instructions

Prerequisites: Python 3.14, Node 22.

Backend (terminal 1):

```bash
cd resume-backend/resume-backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./run.sh
```

The API starts on http://127.0.0.1:8000 with a SQLite database created
automatically. No configuration is required for a first run; to enable the AI
layer locally, create a `.env` with `OPENAI_API_KEY=...` (never commit it).

Frontend (terminal 2):

```bash
cd resume-ui/resume-ui
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server proxies `/api` to the backend
so the browser talks to one origin, exactly as production behaves.

Tests:

```bash
cd resume-backend/resume-backend
.venv/bin/python -m pytest -q
```

## 9. Deployment Details

Deployed on **Google Cloud Platform**, project-isolated, with a deliberately
minimal footprint:

- **Cloud Run** service `proof` (region `us-central1`): the single container,
  `min-instances=0` (scales to zero when idle), `max-instances=1`, 1 GiB
  memory, 300 s request timeout for long AI reviews.
- **Cloud SQL** instance `proof-db`: Postgres 17, smallest tier (db-f1-micro,
  10 GB HDD, single zone, daily backups). Reachable only through the Cloud
  Run connector; no authorized networks.
- **Artifact Registry** repo `proof`: holds the image, with a cleanup policy
  (keep the 3 newest versions, delete older than 30 days).
- **Secret Manager**: `SECRET_KEY`, `OPENAI_API_KEY` and `DATABASE_URL`
  injected as environment variables; no secret ever lives in the repo.
- **Budget alert** at 15 USD/month. Expected bill is about 9 to 11 USD, all
  of it the database; compute stays inside the Cloud Run free tier.

Releases are three steps run locally: build the image for `linux/amd64`, push
it to Artifact Registry, and roll the Cloud Run service to the new image with
`gcloud run deploy`. Cloud Build is intentionally not used. The schema is
created by the app's startup hook on first boot against an empty database.

## 10. Web Application Usage

Open the live URL, create an account, and upload a resume (PDF, DOCX, TXT or
MD, up to 5 MB). Optionally set a target role and paste a job description,
choose whether to include the AI review, and run it. The result page shows
the score, per-category budgets, every finding with its evidence and point
gain, the AI critique when requested, and a printable report. Every past
review stays in History with deltas between runs. Account settings cover
password change, signing out other devices, and password-confirmed account
deletion, which permanently removes every resume, analysis and session the
account owns.

## 11. Docker Instructions

The root [Dockerfile](Dockerfile) is the production image: a Node stage builds
the React app, a Python stage serves it and the API together.

```bash
# build (from the repo root)
docker build -t proof .

# run locally on http://localhost:8080 (SQLite inside the container)
docker run --rm -p 8080:8080 \
  -e SECRET_KEY=any-string-at-least-32-bytes-long-for-dev \
  proof
```

Health check: `curl http://localhost:8080/api/health`.

For Cloud Run the image must be built for `linux/amd64`
(`docker buildx build --platform linux/amd64`), pushed to Artifact Registry,
and deployed with `gcloud run deploy`, passing the secret references and the
Cloud SQL connector flag.

An alternative self-hosted path exists in [docker-compose.yml](docker-compose.yml):
two containers (API plus an nginx-served frontend) on port 8080 with SQLite in
a named volume. Copy `.env.deploy.example` to `.env`, set `SECRET_KEY`, then
`docker compose up --build`.
