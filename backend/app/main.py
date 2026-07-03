"""Network AI — FastAPI entrypoint.

Production-readiness layer: cookie-session auth, per-user data isolation,
plan gates, rate limiting, and security headers — while staying a copilot
(no scraping, no auto-send, no bulk).
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import config
from .db import Base, engine, run_lightweight_migrations
from .routers import (
    auth,
    billing,
    contacts,
    emails,
    events,
    goals,
    linkedin,
    messages,
    next_move,
    opportunities,
    outreach,
    profile,
)

logger = logging.getLogger("app")

# Create tables on startup (simple for MVP; swap for migrations later).
Base.metadata.create_all(bind=engine)
# Add any additive columns to pre-existing tables (idempotent).
run_lightweight_migrations()

app = FastAPI(title="Network AI", version="0.1.0")

# Credentialed CORS requires an explicit origin list (wildcards are invalid).
# Configure via ALLOWED_ORIGINS (comma-separated); defaults to the local frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Practical security headers on every response. CSP is deliberately
    deferred (documented in PRODUCTION_CHECKLIST.md)."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Frame-Options", "DENY")
    if request.url.path.startswith("/auth"):
        # Never let a proxy cache an identity or a session response.
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Never leak stack traces to clients; log them server-side instead."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

app.include_router(auth.router)
app.include_router(billing.router)
app.include_router(events.router)
app.include_router(profile.router)
app.include_router(messages.router)
app.include_router(goals.router)
app.include_router(contacts.router)
app.include_router(emails.router)
app.include_router(linkedin.router)
app.include_router(next_move.router)
app.include_router(outreach.router)
app.include_router(opportunities.router)


@app.get("/health")
def health():
    return {"status": "ok"}
