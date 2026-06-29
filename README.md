# Network AI

> **One-line pitch:** A bilingual (Turkish/English) referral & outreach copilot
> for Turkish junior software engineers targeting Turkey, remote, European, and
> global tech roles.

Network AI helps Turkish junior engineers and CS new grads (1) find
**Turkey-relevant opportunities** — Turkey-based, remote, EMEA/Europe, and global
remote roles they can realistically apply to — (2) judge whether a Turkey-based
candidate can apply, (3) identify who to contact, (4) generate honest
Turkish/English outreach, and (5) track manual follow-up. It works like Cursor:
**AI proposes, you review, approve, edit, copy, and send everything yourself.**

It is **not** a U.S. new-grad platform, **not** "Kariyer.net with AI," and **not**
a generic global job board — it's a narrow workflow tool for the Turkey →
remote/EU job hunt. The default journey starts at **`/opportunities`** and flows
into **`/outreach`**. (A legacy U.S. new-grad matching layer still exists in the
codebase but is off the primary navigation.)

A narrative version lives at **`/pitch`** in the running app.

---

## Investor demo summary

### Problem
Turkish juniors and new grads don't lose interviews because they can't code —
cold applications vanish into ATS black holes. In Turkey referrals matter even
more than in most markets, yet early-career engineers don't know *who* to
contact, *what* to say in English without sounding cringe, or whether a
Turkey-based candidate can even apply to a given remote/EU role.

### Why now
ICT graduates have Turkey's highest emigration rate, and a "virtual brain drain"
is growing — engineers in Istanbul working remotely for European and global teams
for EUR/USD pay. Auto-apply flooded the boards, so the edge shifted from
*applying faster* to *networking better* — exactly where no Turkish platform
helps the individual.

### Solution
Network AI is the **personal outreach workflow layer** for the Turkey → remote/EU
hunt:

- Curates **Turkey-relevant opportunities** (Turkey / remote / EMEA / global) from
  companies' official public ATS APIs, public job feeds, and manual curation.
- Labels each role with a conservative **Turkey-applicability** verdict
  (**Strong fit → Possibly eligible → Unclear → Probably not eligible**) and a
  reason; US-only / EU-citizenship-only roles are hidden by default.
- Tells you **who to contact** with manual search links.
- Drafts honest **bilingual (TR/EN) outreach** personalized with your real skills,
  with a quality checklist and optional Turkey/CET + work-authorization framing.
- Tracks manual follow-up — you approve and send everything yourself.

### Differentiation (why it's not a spam tool)
Copilot, not autopilot: **no scraping, no auto-send, no browser automation, no
bulk sending.** Every message requires explicit approval and is sent manually.
Outcome + follow-up tracking rewards quality over volume.

### Business model (planned — no revenue yet)
- **B2C job seekers:** $9–19/month for tracking, drafting, and reminders.
- **Career coaches:** $49–199/month to manage multiple clients.
- **Universities, bootcamps & clubs:** team/cohort pricing for career centers.

### Intentionally NOT built yet
Payments/billing, user accounts & auth, hosted deployment, LinkedIn integration
of any kind, and automated/bulk email sending. LLM drafting uses the **Claude
Messages API** when `ANTHROPIC_API_KEY` is set and falls back to deterministic
templates otherwise, so the product story — *honest, permission-based
networking* — works fully offline and is provable, not promised.

---

## AI email copilot (permission-based)

Network AI can draft personalized outreach **emails** using your resume, your
job-search goal, the selected job, and a contact you added — then route them
through an approval queue. It is a copilot, never an autopilot:

- **AI proposes, you approve.** Drafts land in `/emails` as proposed actions
  with a "why this contact" rationale, a quality checklist, and a risk
  checklist. Nothing is sent without your explicit approval.
- **Claude by default.** When `ANTHROPIC_API_KEY` is set, drafts are written by
  Claude via the **Anthropic Messages API** (`claude-opus-4-8` by default,
  env-configurable). `OPENAI_API_KEY` enables the OpenAI **Responses API** as an
  optional fallback (no Chat Completions / Assistants / Files / Vector Stores /
  embeddings). Keys are read by the backend only and never logged, returned, or
  committed.
- **Deterministic fallback.** With no key (or on any LLM error / invalid JSON),
  the app falls back to a deterministic template. The draft shows
  `llm_used: true/false` so you always know which path produced it.
- **Manual-first contacts.** You add contacts yourself. A provider abstraction
  (`ManualProvider`, plus `HunterProvider` / `PeopleDataLabsProvider`
  placeholders) is ready for compliant API discovery later — but nothing runs
  unless a key is present, and **no scraping is ever performed**.
- **Gmail sending is disabled by default.** Copy / manual send is the path.

### Environment variables

Copy `backend/.env.example` to `backend/.env` and fill in what you need. All AI
features degrade gracefully when blank.

| Variable | Purpose | Default |
| --- | --- | --- |
| `LLM_PROVIDER` | Preferred provider (`anthropic` or `openai`) | `anthropic` |
| `ANTHROPIC_API_KEY` | Enables LLM drafting via Claude (Messages API) | _(blank → fallback)_ |
| `ANTHROPIC_MODEL` | Claude model id | `claude-opus-4-8` |
| `OPENAI_API_KEY` | Optional fallback provider (Responses API) | _(blank → off)_ |
| `OPENAI_MODEL` | Model id for the OpenAI Responses API | `gpt-4.1-mini` |
| `HUNTER_API_KEY` | Optional compliant discovery provider | _(blank → off)_ |
| `PDL_API_KEY` | Optional compliant discovery provider | _(blank → off)_ |
| `GMAIL_SEND_ENABLED` | Must be `true` to even consider sending | `false` |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Future Gmail OAuth | _(blank)_ |

> The backend reads `.env` via `python-dotenv` and **never** writes or logs it.
> Secrets stay server-side; the frontend never sees an API key.

### Enabled now vs. placeholder

- **Enabled now:** goals CRUD, manual contacts, compliant-discovery aggregation
  (manual results + "not configured" message), AI/deterministic email drafting,
  full email approval queue (edit/approve/reject/copy/mark-sent), outcome &
  follow-up tracking, visible guardrails and soft limits.
- **Placeholder (architecture only):** Hunter / PDL network calls, and Gmail
  sending (returns a friendly "disabled" message; no OAuth/SMTP implemented).

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

## Vibe Mode

Networking outreach is boring and stressful, so **Vibe Mode** (`/vibe`, also on
the dashboard) turns it into a focused **25-minute sprint**: pick a mood, start
the timer, and work a short checklist (review strong matches → approve drafts →
copy/manual-send → update outcomes) with music playing alongside.

- **No hosted audio.** Network AI does **not** host or serve any music files.
- **Third-party embeds only.** Each mood loads a Spotify / SoundCloud / YouTube
  **embedded player** (iframe). The default playlists are curated, swappable
  defaults — change a mood's `embedUrl` in `frontend/lib/vibe.ts`.
- **No autoplay.** Music never starts on its own; the embedded player requires
  you to press play.
- **Same rules.** Vibe Mode only changes pacing and atmosphere — the philosophy
  is unchanged: no scraping, no auto-send, no bulk sending, manual approval only.

### Momentum (gamification)

**Momentum** is a tasteful points layer that rewards *quality* networking
progress — never volume or spam. You earn points only for milestones you
confirm by hand:

| Action | Momentum |
| --- | --- |
| Draft approved | +5 |
| Marked ready to send (copied) | +5 |
| Sent manually | +10 |
| Follow-up completed | +10 |
| Reply received | +25 |
| Referral received | +50 |
| Interview received | +100 |
| Ignored / rejected | +0 (logged, no shame) |

- A **"Today's Momentum"** card on the dashboard shows points today, total
  points, your day streak, and recent wins.
- Marking an outcome shows a short celebration toast (bigger for an interview)
  and an **optional** chime synthesized with the Web Audio API — **no
  copyrighted or hosted audio, no autoplay** (sounds only play from your click),
  with a **mute toggle** persisted in `localStorage`.
- Points are stored in a `momentum_events` table and **awarded once** per
  milestone, so clicking the same outcome twice never double-counts.
- By design, Momentum rewards quality, not quantity: **no scraping, no
  auto-send, no bulk sending, and replies are never auto-detected** — every
  outcome is tracked manually.

---

## Next Move AI

Outreach doesn't end when you hit send — the hard part is knowing what to do
when someone *replies*. **Next Move AI** (`/next-move`) helps with that, while
staying strictly permission-based:

- You **manually paste** the reply you received (from a recruiter, engineer,
  alumnus, or hiring manager). The app never reads LinkedIn or your inbox.
- The backend (**Claude Messages API** by default, OpenAI Responses API as
  optional fallback, with a deterministic keyword fallback otherwise) returns a
  **summary**, a detected **intent** (positive, neutral,
  negative, referral possible, interview related, asks for resume, asks for work
  authorization, needs follow-up), an **urgency**, a **recommended next move**,
  **risk notes**, a **suggested pipeline update**, and a drafted reply in both
  **email** and **short-message** styles — each with a quality + safety checklist.
- You review and edit the draft, **copy** it, and send it yourself. If you linked
  a pipeline item, one click logs the outcome (replied / referral received /
  interview received) and awards **Momentum** once (no double-counting).
- Guardrails are unchanged: no scraping, no browser automation, no auto-reading
  of messages, no Gmail sending, no auto-send. AI proposes; you approve and send.

---

## Opportunities feed (`/opportunities`)

A feed of **real Turkey + Remote/EU listings for junior Turkish engineers** that
flows directly into the outreach copilot. It is **not** a generic job board, and
it serves **real listings only** — no fake/sample data.

- **Compliant sources, pulled in one click.** "Refresh live sources"
  (`POST /opportunities/refresh-all`) fetches from companies' **official public
  ATS APIs** (Lever — Dream Games, Codeway, Commencis; plus Greenhouse/Ashby
  adapters) **and** keyless **public job APIs** (Arbeitnow, Remotive, Jobicy).
  A manual JSON import endpoint (`POST /opportunities/import`) is also available.
  These are the official embed APIs companies publish — **no scraping** of
  LinkedIn, Kariyer.net, Youthall, Techcareer, Coderspace, or any protected site;
  no browser automation, no auto-apply, no auto-send. Each fetch is independently
  resilient: one source failing never breaks the others.
- **`GET /opportunities` never makes a network call** — it serves stored rows.
  The app does **not** auto-seed any demo data; an empty feed prompts you to
  refresh live sources.
- **Most-desired employers as a directory.** Companies without a public ATS
  (Google, Amazon, Microsoft, McKinsey/BCG/Bain, İş Bankası, Garanti BBVA,
  Akbank, Trendyol, Getir, …) are listed with a careers link only — **no jobs are
  fetched** and **no board tokens are invented**.
- **Level + Field lanes.** Tabs separate **New grad / Internships / Junior** and
  **Engineering / Business**, so tech and business students each see only relevant
  roles (creative/admin "other" roles are hidden by default).
- **Conservative "Turkey-applicability" label** on every role — *Strong fit /
  Possibly eligible / Unclear / Probably not eligible* — with a one-line reason.
  US / North-America-located and EU-citizenship-only roles are flagged *Probably
  not eligible* and hidden by default. **Always verify eligibility on the company
  page** — the label is a guess, not advice.
- **"Draft outreach"** on a role prefills the `/outreach` copilot (company, role,
  description, target region, and language default — Turkish for domestic roles,
  English for remote/EU/global, with the Turkey/CET line on for remote/EU).

## Tech stack

| Layer     | Technology                                            |
| --------- | ----------------------------------------------------- |
| Backend   | FastAPI, SQLAlchemy, SQLite, Pydantic (Python 3.11+)  |
| Frontend  | Next.js 14 (App Router), React 18, TypeScript, Tailwind |
| Matching  | Deterministic keyword scoring (no LLM)                |
| Messaging | Claude (Anthropic) drafting + deterministic checklist |

Matching is deterministic and offline. Message/email/outreach **drafting** uses
the **Claude Messages API** when `ANTHROPIC_API_KEY` is set, and falls back to
deterministic templates otherwise — so every AI feature degrades gracefully with
no key. The `llm_used` flag on each draft tells you which path produced it.

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

**Primary (Turkey → remote/EU) endpoints:**

| Method | Path                                   | Purpose                              |
| ------ | -------------------------------------- | ------------------------------------ |
| GET    | `/opportunities`                       | Ranked feed (filters: `region`, `seniority`, `function`, `applicability`, …) |
| GET    | `/opportunities/sources`               | Source registry (live ATS + directory) |
| POST   | `/opportunities/refresh-all`           | Pull all sources: ATS + public APIs  |
| POST   | `/opportunities/refresh-sources`       | Refresh official ATS boards only      |
| POST   | `/opportunities/refresh-public-sources`| Refresh Arbeitnow / Remotive / Jobicy |
| POST   | `/opportunities/import`                | Manual JSON import (no scraping)     |
| POST   | `/outreach/draft-from-paste`           | Paste-a-JD bilingual outreach draft  |

**Legacy (U.S. new-grad layer, off primary nav):**

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
| GET/POST | `/goals`                             | List / create job-search goal        |
| PATCH/DELETE | `/goals/{id}`                    | Update / delete a goal               |
| POST   | `/contacts/manual`                     | Add a contact manually               |
| GET    | `/contacts`                            | List contacts (optional `?job_id=`)  |
| GET    | `/contacts/{id}`                       | Contact detail                       |
| POST   | `/contacts/discover`                   | Compliant discovery (manual + providers) |
| POST   | `/emails/draft`                        | Draft an email (LLM or fallback)     |
| GET    | `/emails`                              | List email drafts (approval queue)   |
| GET    | `/emails/{id}`                         | Email draft detail                   |
| PATCH  | `/emails/{id}`                         | Edit body/subject, set outcome/follow-up |
| POST   | `/emails/{id}/approve` · `/reject`     | Approve / reject a draft             |
| POST   | `/emails/{id}/mark-copied` · `/mark-sent-manual` | Manual send workflow       |
| POST   | `/emails/{id}/send-gmail`              | Disabled placeholder (friendly message) |

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

## AI email copilot — demo flow

1. **Profile** → upload/paste a resume.
2. **Goals** → create a goal, e.g. "Backend/AI engineer role in NYC or remote",
   outreach goal = advice.
3. **Jobs** → ingest, then **Matches** → match all.
4. Open a **Strong Target** → review the outreach strategy.
5. In **Contacts & AI Email Outreach**: add a recruiter/engineer contact (or run
   discovery — without provider keys it shows the "not configured" message and
   your manual contacts).
6. Click **Draft Email**. If `OPENAI_API_KEY` is set the body is written by the
   OpenAI Responses API (`llm_used: true`); otherwise it's a deterministic
   template (`llm_used: false`).
7. Review the **why this contact**, **quality checklist**, and **risk
   checklist**; edit; **Approve**; **Copy Email** or **Mark Sent Manually**.
8. Track the **outcome** and **follow-up** on the draft. (Gmail send stays
   disabled.)

## Limitations (stated honestly)

- Contact discovery requires a compliant provider API key or manual input —
  there is **no scraping** of LinkedIn or any website.
- Gmail sending is **disabled by default**; this MVP prefers copy / manual send.
- No auto-send and no bulk-send anywhere in the product.
- LLM drafting uses the **Claude Messages API** by default (OpenAI Responses API
  as an optional fallback); deterministic templates are used when no key is set.
- This is a **local-first demo**, not production SaaS. A real version needs:
  auth, encryption at rest, OAuth for any sending, rate limits, an
  unsubscribe / do-not-contact list, a privacy policy, and a proper compliance
  review before any outreach at scale.

## Future roadmap

- Implement compliant provider discovery (Hunter / PDL) behind keys.
- Safe Gmail OAuth send (approved + explicit confirm only), still no bulk.
- Richer resume parsing (education, target roles, seniority).
- Job descriptions for deeper match scoring beyond the title.
- Export pipeline to CSV; weekly networking digest.
- Multi-user support with auth (out of scope for this MVP).

---

> Network AI never auto-sends or scrapes. It proposes drafts and manual search
> links; you review, edit, copy, and send everything yourself.
