# Deployment — validation-sprint checklist

Goal: get the current app onto a public URL so strangers can sign up during the
7-day validation sprint. Stack: FastAPI + SQLite (backend) and Next.js 14
(frontend). No Docker required; any Python host + Vercel works.

Suggested pairing: **backend on Fly.io or Railway** (anything that runs a
Python process and mounts a persistent volume), **frontend on Vercel**.

---

## 1. Backend

### Run command

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

**Exactly one worker.** Rate limiting is in-process memory
(`app/services/rate_limit.py`); multiple workers would each get their own
counters. Fine for the beta — documented in `PRODUCTION_CHECKLIST.md`.

Tables and additive columns are created automatically on startup
(`Base.metadata.create_all` + `run_lightweight_migrations()` in `app/main.py`).
There is no separate migration step.

### Required environment variables (backend)

| Variable | Value for production | Why |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | your key | Claude writes the outreach drafts. Without it the app silently falls back to deterministic templates (`llm_used: false`) — set it for the sprint. |
| `ANTHROPIC_MODEL` | optional | Defaults to `claude-opus-4-8`. `claude-sonnet-5` is a good cost/latency trade. |
| `ALLOWED_ORIGINS` | `https://<your-frontend>.vercel.app` | Credentialed CORS needs the exact frontend origin(s), comma-separated. No wildcard. |
| `COOKIE_SECURE` | `true` | Session cookie is HttpOnly + SameSite=Lax; `Secure` requires HTTPS (any real host has it). |
| `TRUST_PROXY` | `true` | Honors `X-Forwarded-For` from the platform's proxy so rate limits / audit log see real client IPs. |
| `DATABASE_URL` | `sqlite:////data/network_ai.db` | Point the SQLite file at a **persistent volume**, or the DB resets on every deploy. |
| `SESSION_TTL_DAYS` | optional (default 30) | Session lifetime. |

Leave unset/off: `OPENAI_API_KEY` (optional fallback), `HUNTER_API_KEY` /
`PDL_API_KEY` (contact discovery stays manual), `GMAIL_SEND_ENABLED` (stays
`false` — copy/manual send only), `RATE_LIMIT_DISABLED` (never set in prod).

### Database setup

SQLite, zero setup — just make `DATABASE_URL` point inside a persistent volume:

- **Fly.io:** `fly volumes create data --size 1`, mount at `/data`, set
  `DATABASE_URL=sqlite:////data/network_ai.db` (note the four slashes —
  absolute path).
- **Railway/Render:** attach a volume, same idea.

Back it up during the sprint with a copy: it's one file.

### Seed real listings (once, after first deploy)

The feed self-seeds 14 sample rows so it's never empty, but real users should
see real jobs. Sample rows are hidden automatically once real rows exist, so
right after the first deploy, sign up and pull the live sources:

```bash
# from your machine, using your own account's session cookie via the UI:
#   Opportunities page → "Refresh live sources"
# or via curl after logging in and capturing the na_session cookie:
curl -X POST https://<backend-host>/opportunities/refresh-all \
  -H "Cookie: na_session=<your-session-token>"
```

This imports from the verified Lever/Greenhouse boards + public APIs
(~2,000+ rows). Re-run it every day or two during the sprint (it's
rate-limited to 2/min and dedupes on re-import).

### Admin account (to read the validation scoreboard)

```bash
cd backend
.venv/bin/python scripts/create_user.py you@example.com '<strong-password>' --plan admin
# or promote an existing account:
curl -X POST https://<backend-host>/billing/set-plan \
  -H "Cookie: na_session=<admin-session>" -H "Content-Type: application/json" \
  -d '{"email": "someone@example.com", "plan": "pro"}'
```

Scoreboard: `GET /events/summary` (admin only) returns per-event totals +
unique users, and eligibility-label feedback tallies with the latest "wrong"
reasons. This is the funnel for the sprint:
`signup_completed → resume_uploaded → opportunity_viewed → draft_created →
pipeline_saved → pro_button_clicked → mock_checkout_viewed`.

---

## 2. Frontend

### Deploy (Vercel)

```bash
cd frontend
npm install
npx vercel --prod    # or connect the repo in the Vercel dashboard
```

### Required environment variables (frontend)

| Variable | Value |
| --- | --- |
| `NEXT_PUBLIC_API_BASE` | `https://<backend-host>` (no trailing slash) |

Set it in the Vercel project settings, then redeploy. The API client
(`frontend/lib/api.ts`) sends `credentials: "include"` on every request, so
CORS + cookies only work when `ALLOWED_ORIGINS` on the backend exactly matches
the deployed frontend origin and `COOKIE_SECURE=true`.

### Cookie/CORS gotchas (the usual failure modes)

- Frontend and backend are on **different domains** → the session cookie is
  cross-site in the browser's eyes only if you misconfigure: it is set by the
  *backend's* domain and sent back to the backend, so SameSite=Lax works as
  long as all API calls go to the backend origin (they do). Nothing extra
  needed.
- 401s right after login → `ALLOWED_ORIGINS` doesn't exactly match the frontend
  origin (scheme + host), or `COOKIE_SECURE=true` while testing over plain HTTP.
- Every response should carry `access-control-allow-credentials: true` for the
  frontend origin; if not, re-check `ALLOWED_ORIGINS`.

---

## 3. Verify before sharing the URL

### Tests + build

```bash
# Backend (152+ tests)
cd backend && .venv/bin/python -m pytest tests -q

# Frontend type check + production build
cd frontend && npx tsc --noEmit && npm run build
```

### Smoke test the full loop (on the deployed URL, as a fresh user)

1. **Signup** at `/signup` with a throwaway email → lands in the app, plan badge shows `free`.
2. **Resume** at `/profile` → paste or upload a resume → skills chips appear.
3. **Opportunities** at `/opportunities` → real listings show (no "Sample listing" badges); skill-match reasons appear on cards; click ✓/✗ on an eligibility label → "Thanks — noted ✓".
4. **Draft** → "Draft outreach" on a card → `/outreach` prefilled → "Draft outreach" → draft appears with the **"AI-written (Claude)"** badge (if it says "Template (no AI key set)", `ANTHROPIC_API_KEY` isn't reaching the backend).
5. **Pipeline** → "Save to pipeline" → item appears at `/pipeline`; mark sent / replied works.
6. **Fake door** → `/pricing` → "Upgrade to Pro" → honest "payments aren't live" notice shows.
7. **Scoreboard** → as the admin account: `GET /events/summary` shows every step above counted once.

If all seven pass, the product is validation-ready. Point the landing-page
CTA (see `validation/landing-page.md`) at the deployed `/signup`.

---

## 4. Still requires you (credentials / accounts)

- Hosting accounts (Fly.io/Railway + Vercel) and the domain, if any.
- `ANTHROPIC_API_KEY` from console.anthropic.com (set a spend limit).
- Creating the admin user and running the first `refresh-all`.
- Daily: check `/events/summary`, re-run `refresh-all`, back up the SQLite file.
