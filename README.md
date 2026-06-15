# Network AI

> **One-line pitch:** A permission-based networking copilot that turns new job
> postings into working actions — for new grads and international students.

Network AI helps you run a focused, honest job-search outreach process. It
ingests new-grad jobs, ranks them against your resume profile, drafts outreach
messages, and tracks every contact through a lightweight CRM pipeline — all
while keeping you in full control. The product works like Cursor: **AI
proposes, you review, approve, edit, copy, and send everything yourself.**

A narrative version of everything below lives at **`/pitch`** in the running app
(useful as a demo/investor link).

---

## Investor demo summary

### Problem
New grads and international students don't lose offers because they can't code —
they lose them because applications vanish into ATS black holes. Referrals and
warm intros convert; most students don't know who to contact, what to say, or
when to follow up.

### Why now
Auto-apply tools flooded job boards, so a single posting draws thousands of
one-click applications within hours. Recruiters respond by leaning even harder on
referrals. The edge has shifted from *applying faster* to *networking better* —
and auto-apply is the wrong tool for that.

### Solution
Network AI is the **networking layer**, not another auto-apply bot:

- Ranks fresh new-grad roles against your resume with a transparent rubric.
- Labels each role (**Strong Target → Worth Networking → Low Priority → Poor
  Fit**) and gives a concrete **next best action**.
- Produces a deterministic **outreach strategy**: who to contact first, how many
  people, what tone, advice vs. referral, and a step sequence.
- Drafts four message types with a **quality checklist** that flags fake
  personalization and weak asks.
- Tracks the funnel: **Jobs → Strong matches → Drafts → Sent → Replies →
  Interviews**, plus follow-ups and outcomes.

### Differentiation (why it's not a spam tool)
Copilot, not autopilot: **no scraping, no auto-send, no browser automation, no
bulk sending.** Every message requires explicit approval and is sent manually.
Outcome + follow-up tracking rewards quality over volume.

### Business model (planned — no revenue yet)
- **B2C job seekers:** $9–19/month for tracking, drafting, and reminders.
- **Career coaches:** $49–199/month to manage multiple clients.
- **Universities, bootcamps & clubs:** team/cohort pricing for career centers.

### Intentionally NOT built yet
Payments/billing, user accounts & auth, hosted deployment, any LLM API calls,
LinkedIn integration of any kind, and email/automated sending. The MVP is
deliberately local, deterministic, and offline so the product story — *honest,
permission-based networking* — is provable, not promised.

---

## Safety & compliance philosophy

Network AI is deliberately **not** a spam bot. The constraints below are
product features, not limitations:

- **No LinkedIn scraping.** Contact suggestions are *manual* Google/LinkedIn
  search links you open yourself.
- **No auto-sending.** Nothing is ever sent on your behalf. You copy approved
  drafts and send them manually.
- **No browser automation.** No headless browsers, no bots.
- **No fake personalization.** Templates never invent shared history, schools,
  or claims like "we met." A quality checklist flags anything risky.
- **You review everything.** Every draft moves through an explicit
  draft → approve/reject → copy → mark-sent-manually workflow.
- **Local-first.** Data lives in a local SQLite file. There is no auth, no
  payments, and no deployment in this MVP.

---

## Tech stack

| Layer     | Technology                                            |
| --------- | ----------------------------------------------------- |
| Backend   | FastAPI, SQLAlchemy, SQLite, Pydantic (Python 3.11+)  |
| Frontend  | Next.js 14 (App Router), React 18, TypeScript, Tailwind |
| Matching  | Deterministic keyword scoring (no LLM)                |
| Messaging | Deterministic templates + quality checklist (no LLM)  |

Everything is deterministic and offline — there are **no LLM API calls** in
this MVP.

---

## Local setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the API (http://localhost:8000, docs at /docs)
uvicorn app.main:app --reload --port 8000
```

The SQLite database (`network_ai.db`) and any new columns are created
automatically on startup.

### Frontend

```bash
cd frontend
npm install

# Run the dev server (http://localhost:3000)
npm run dev
```

The frontend talks to `http://localhost:8000` by default; override with
`NEXT_PUBLIC_API_BASE` in `frontend/.env.local`.

### Tests / verification

```bash
# Frontend type check + production build
cd frontend
npx tsc --noEmit
npm run build

# Backend import / route smoke check
cd backend
.venv/bin/python -c "from app.main import app; print(len(app.routes), 'routes')"
```

---

## Demo flow

1. Start the backend and frontend (commands above).
2. Open **http://localhost:3000**.
3. Click **Load demo data** on the dashboard (seeds a profile, jobs, matches,
   and drafts instantly) — or do it manually:
   - **Profile** → paste a resume → *Save Profile*.
   - **Jobs** → *Ingest Latest New Grad Jobs*.
   - **Matches** → *Match All Jobs*.
4. Open a top match → read the **Next Best Action** and **Outreach Strategy**,
   then **Generate Outreach Drafts** (4 message types, each tone-labeled).
5. **Messages** → review each draft against its quality checklist, edit,
   *Approve*, *Copy*, then *Mark Sent Manually*.
6. After you reach out, mark the real **outcome** (replied, interview, etc.) and
   set a **follow-up** reminder if needed.
7. **Pipeline** → watch contacts flow across the CRM board, follow-ups-due band,
   and outcomes band.
8. **Dashboard** → see "Today's networking plan" and "Your networking funnel"
   update from your local data. Open **`/pitch`** for the narrative.

---

## API endpoints

| Method | Path                                   | Purpose                              |
| ------ | -------------------------------------- | ------------------------------------ |
| GET    | `/health`                              | Health check                         |
| POST   | `/profile/resume-text`                 | Save/replace resume, extract profile |
| GET    | `/profile`                             | Get the saved profile                |
| POST   | `/jobs/ingest/simplify`                | Ingest SimplifyJobs new-grad roles   |
| GET    | `/jobs`                                | List jobs                            |
| GET    | `/jobs/{id}`                           | Job detail                           |
| GET    | `/jobs/{id}/contact-searches`          | Manual contact search links          |
| GET    | `/jobs/{id}/strategy`                  | Deterministic outreach strategy      |
| POST   | `/jobs/match-all`                      | Rank all jobs vs. profile            |
| POST   | `/jobs/{id}/match`                     | Rank a single job                    |
| GET    | `/jobs/matches/ranked`                 | Ranked matches (with breakdown)      |
| POST   | `/messages/generate`                   | Generate 4 draft variants for a job  |
| GET    | `/messages`                            | List drafts (with quality checklist) |
| PATCH  | `/messages/{id}`                       | Edit a draft                         |
| POST   | `/messages/{id}/approve`               | Approve a draft                      |
| POST   | `/messages/{id}/reject`                | Reject a draft                       |
| POST   | `/messages/{id}/mark-copied`           | Mark copied                          |
| POST   | `/messages/{id}/mark-sent-manually`    | Mark manually sent                   |
| POST   | `/messages/{id}/outcome`               | Record a real-world outcome          |
| POST   | `/messages/{id}/follow-up`             | Set/clear follow-up state + due date |
| GET    | `/outcomes`                            | Outcome counts + reported messages   |
| GET    | `/stats`                               | Dashboard aggregates + funnel        |
| POST   | `/demo/seed`                           | Seed demo data (offline, idempotent) |

Supported outcomes: `connected`, `replied`, `referral_received`,
`interview_received`, `ignored`, `rejected`.

---

## Screenshots

_Add screenshots here:_

- `docs/dashboard.png` — Dashboard with stats, top matches, recent drafts
- `docs/matches.png` — Ranked matches with score breakdown
- `docs/messages.png` — Drafts with quality checklist + outcome tracking
- `docs/pipeline.png` — Networking pipeline CRM board

---

## Future roadmap

- Optional LLM-assisted drafting (still user-reviewed, never auto-sent).
- Richer resume parsing (education, target roles, seniority).
- Job descriptions for deeper match scoring beyond the title.
- Saved contacts per company and per-message reminders.
- Export pipeline to CSV.
- Multi-user support with auth (out of scope for this MVP).

---

> Network AI never auto-sends or scrapes. It proposes drafts and manual search
> links; you review, edit, copy, and send everything yourself.
