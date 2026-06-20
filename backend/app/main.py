"""Network AI — FastAPI entrypoint.

Local MVP backend skeleton. No auth, no LLM calls yet.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, engine, run_lightweight_migrations
from .routers import (
    contacts,
    dashboard,
    demo,
    emails,
    events,
    goals,
    insights,
    jobs,
    linkedin,
    meetings,
    messages,
    momentum,
    next_move,
    profile,
)

# Create tables on startup (simple for MVP; swap for migrations later).
Base.metadata.create_all(bind=engine)
# Add any additive columns to pre-existing tables (idempotent).
run_lightweight_migrations()

app = FastAPI(title="Network AI", version="0.1.0")

# Frontend will run on localhost:3000 (Next.js).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile.router)
app.include_router(jobs.router)
app.include_router(messages.router)
app.include_router(insights.router)
app.include_router(demo.router)
app.include_router(goals.router)
app.include_router(contacts.router)
app.include_router(emails.router)
app.include_router(linkedin.router)
app.include_router(momentum.router)
app.include_router(next_move.router)
app.include_router(dashboard.router)
app.include_router(events.router)
app.include_router(meetings.router)


@app.get("/health")
def health():
    return {"status": "ok"}
