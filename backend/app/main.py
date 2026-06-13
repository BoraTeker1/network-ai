"""Network AI — FastAPI entrypoint.

Local MVP backend skeleton. No auth, no LLM calls yet.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, engine
from .routers import jobs, messages, profile

# Create tables on startup (simple for MVP; swap for migrations later).
Base.metadata.create_all(bind=engine)

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


@app.get("/health")
def health():
    return {"status": "ok"}
