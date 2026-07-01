# Production Readiness Checklist

Honest status of what this codebase does and does not give you. "Done" means
implemented and tested locally — **not** "battle-tested at scale."

## Done in this codebase

- [x] **Auth**: email+password signup/login/logout, scrypt password hashing
      (stdlib, salted, params embedded), opaque server-side sessions (SHA-256
      of token stored, 30-day expiry, revocable), HttpOnly SameSite=Lax cookie.
- [x] **User isolation**: every user-owned query filters by the authenticated
      user; foreign IDs return 404; cross-user access covered by tests.
- [x] **Plans**: free/pro/admin on the user; server-side feature gates (402 +
      structured payload); usage tracking; env-tunable limits.
- [x] **Billing**: mock provider only. Checkout NEVER fakes success; plan
      changes are admin-only and audited. Stripe is a documented TODO
      (`backend/app/routers/billing.py`).
- [x] **Rate limiting**: fixed-window per-user (per-IP for auth + anonymous),
      429 + Retry-After, env-configurable, audit on abuse.
- [x] **Hardening**: input max-lengths, upload type/size validation before
      parsing, CORS from env, security headers (API + frontend), generic 500s
      (traces logged server-side only), audit log without sensitive content.
- [x] **Admin/dev**: `backend/scripts/create_user.py` (with
      `--claim-demo-data` for pre-auth rows).

## Configure BEFORE deploying (hard requirements)

- [ ] `ALLOWED_ORIGINS` = your real frontend origin(s). Never `*`.
- [ ] `COOKIE_SECURE=true` (HTTPS only — the cookie won't work over plain HTTP).
- [ ] **Deploy frontend + API under ONE registrable domain** (e.g.
      `app.example.com` + `api.example.com`). The SameSite=Lax session cookie
      is NOT sent cross-site — different registrable domains (vercel.app +
      fly.dev) will silently break auth. If you truly can't, switch the cookie
      to `SameSite=None; Secure` and re-review CSRF (you lose the Lax defense).
- [ ] `TRUST_PROXY=true` **only** if behind a proxy/load balancer you control
      (otherwise X-Forwarded-For lets clients spoof rate-limit keys).
- [ ] Run a **single uvicorn worker** (rate-limit counters are in-process), or
      move rate limiting to Redis before scaling out.
- [ ] Create your admin account: `python scripts/create_user.py you@… "…" --plan admin`.
- [ ] `ANTHROPIC_API_KEY` set server-side only; confirm nothing logs it.
- [ ] Backend tests green: `cd backend && .venv/bin/python -m pytest -q`.
- [ ] Frontend build green: `cd frontend && npx tsc --noEmit && npm run build`.

## Deliberately NOT done — required before a real public launch

- [ ] **Stripe** (test → live): checkout session, webhook with signature
      verification, plan updates only from verified server-side events.
- [ ] **Email verification** — right now any email can be claimed unverified.
      Acceptable for a hand-invited beta, not for public signup.
- [ ] **Password reset** — needs an email provider; currently an admin must
      intervene. Same beta-only caveat.
- [ ] **Postgres** — SQLite is fine for a single-node beta with backups, but
      move to Postgres before concurrency/scale matters. (SQLAlchemy is
      already the ORM; the migration is mostly config + a data copy.)
- [ ] **Database backups** — at minimum a cron copying `network_ai.db`
      off-machine daily; test a restore once.
- [ ] **Content-Security-Policy** — deferred (Next.js inline scripts need a
      nonce strategy). X-Frame-Options/nosniff/Referrer-Policy are in place.
- [ ] **Session rotation on login** + optional "log out everywhere".
- [ ] **Redis rate limiting** when moving past one worker.
- [ ] **Log aggregation/alerting** — audit events are in the DB; server logs
      go to stdout. Ship them somewhere durable and watch `login_failed` /
      `rate_limited` spikes.
- [ ] **Privacy policy + terms** — you're storing résumés (PII) for real
      users; KVKK (Türkiye) and GDPR (EU users) both apply. Add data-deletion
      on request (a `DELETE /auth/me` account-wipe endpoint is a good first
      step) before charging money.
- [ ] **Dependency/CVE scanning** (pip-audit / npm audit) in CI.

## Honest limitations to keep in mind

- The mock billing provider means **no revenue collection exists yet** — Pro
  is granted manually. That's by design until WTP is validated.
- Rate limits reset on process restart and are per-process.
- CSRF posture relies on SameSite=Lax + strict CORS + JSON-only mutations —
  solid for this architecture, but re-evaluate if you ever add form posts or
  `SameSite=None`.
- Legacy pre-auth rows (`user_id='demo-user'`) are invisible to real accounts
  unless claimed via the admin script.
