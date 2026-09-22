# Network AI

A FastAPI backend that ingests new-grad software engineering postings, parses a pasted
resume into a structured skill profile, and ranks every stored job against that profile with
a deterministic, explainable scorer.

The scoring deliberately makes no LLM calls. Every point a job receives is attributable to a
rule, so the same resume and the same job always produce the same score. The API
returns the reasoning behind it as well as the number itself.

## Stack

Python 3 · FastAPI · SQLAlchemy 2 · Pydantic 2 · SQLite · Requests

## How it works

```
resume text ──► resume_parser ──► Profile (skills, summary)
                                       │
SimplifyJobs README ──► job_ingestion ─┼──► matcher ──► JobMatch (score + reasons)
      (HTML tables)      (dedup, store)│
                                    Job rows
```

**Ingestion** (`services/job_ingestion.py`) pulls the
[SimplifyJobs/New-Grad-Positions](https://github.com/SimplifyJobs/New-Grad-Positions) README
and parses it. The postings live in HTML `<table>` rows rather than Markdown tables, and a
company cell of `↳` means "same company as the row above", so the parser carries the last
company forward, strips decorative markers, unescapes entities, and pulls the first `href`
as the real application URL. Rows without a company, role, or link are skipped rather than
stored half-empty.

**Deduplication** hashes `company | role | location | url` into a SHA-1 `external_id`,
enforced both within a single ingest batch and against a `UNIQUE(source, external_id)`
constraint in the database. Re-running ingestion is therefore safe and reports how many rows
it skipped.

**Resume parsing** (`services/resume_parser.py`) matches against a canonical skill list using
token-aware lookaround regexes, so `Java` does not match inside `JavaScript` and `AWS` does
not match inside `flaws`.

**Matching** (`services/matcher.py`) scores each job out of 100:

| Signal | Max | Basis |
|---|---|---|
| Skill overlap | 50 | Proportion of profile skills appearing in the job text |
| Role-title fit | 25 | 25 for a backend/AI/SWE title, 12 for a generic engineering title |
| Entry-level signal | 15 | "new grad", "entry level", "junior", a trailing `I`/`1`, etc. |
| Location | 10 | 10 remote, 5 known location, 0 unknown |

Each match stores a human-readable explanation plus matched and missing skills, so
`GET /jobs/matches/ranked` returns *why* a job scored what it did.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness check. |
| `POST` | `/profile/resume-text` | Save/replace the resume; returns the parsed profile. Upserts, so re-pasting does not create duplicates. |
| `GET` | `/profile` | Return the saved profile. |
| `POST` | `/jobs/ingest/simplify` | Fetch, parse, dedupe and store postings. |
| `GET` | `/jobs` | List stored jobs, newest first (`limit`, `offset`). |
| `GET` | `/jobs/{job_id}` | Fetch one job. |
| `POST` | `/jobs/match-all` | Score every stored job against the profile. |
| `POST` | `/jobs/{job_id}/match` | Score a single job (upserts the match). |
| `GET` | `/jobs/matches/ranked` | Jobs joined with scores, highest first. |

Static routes are declared before `/jobs/{job_id}` so the integer path parameter does not
swallow `/jobs/matches/ranked`.

Failure modes are mapped rather than leaked: a failed upstream fetch returns 502, scoring
without a saved profile returns 400, and an unknown job id returns 404.

## Running locally

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Interactive docs at `http://localhost:8000/docs`. Tables are created on startup and data
lands in a local `network_ai.db` SQLite file. `.env.example` documents the environment
variables; none are required to run the current feature set.

```bash
curl -X POST localhost:8000/jobs/ingest/simplify
curl -X POST localhost:8000/profile/resume-text \
  -H 'Content-Type: application/json' \
  -d '{"resume_text": "... your resume ..."}'
curl -X POST localhost:8000/jobs/match-all
curl localhost:8000/jobs/matches/ranked
```

CORS is open to `http://localhost:3000` for a Next.js frontend that is not part of this
repository.

## Status

Ingestion, resume parsing, matching and ranking are implemented and working. The rest is
scaffolding, and the code says so rather than pretending otherwise:

- **Message generation is not implemented.** `services/message_generator.py` defines its
  interface and raises `NotImplementedError`; `/messages` returns a draft count and nothing
  else. The `Message` and `OutreachEvent` models and their approval workflow
  (`draft → approved/rejected → sent`) exist in the schema ahead of the logic.
- **No authentication.** Every record belongs to a single hardcoded `DEMO_USER_ID`.
- **No tests yet.** `job_ingestion.parse_jobs` and `matcher.score_job` are both pure
  functions over their inputs, which is where testing should start.
- **`create_all` on startup, not migrations.** Fine for local development, would need
  Alembic before anything real.

The intended next slice is drafting outreach messages for high-scoring matches, with every
draft requiring manual approval before use. Contact discovery is scoped to generating
LinkedIn/Google search links, with no scraping and no automated sending.
