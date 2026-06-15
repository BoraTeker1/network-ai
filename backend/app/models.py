"""SQLAlchemy ORM models for Network AI.

Tables: profiles, jobs, job_matches, messages, outreach_events.
v1 has no auth, so we hardcode a single demo user.
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .db import Base

# No auth in v1 — every record belongs to this fake user.
DEMO_USER_ID = "demo-user"

# Real-world outreach results the user can report on a sent message.
OUTCOMES = (
    "connected",
    "replied",
    "referral_received",
    "interview_received",
    "ignored",
    "rejected",
)

# Follow-up workflow states — separate from `outcome` so the CRM can nudge the
# user to follow up without overloading the outcome vocabulary. "none" means no
# follow-up is being tracked yet.
FOLLOW_UP_STATUSES = (
    "none",
    "follow_up_needed",
    "followed_up",
    "no_response",
)


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, default=DEMO_USER_ID)

    raw_resume = Column(Text, nullable=True)
    # Simple extracted fields. Lists are stored as JSON-encoded text for now.
    skills = Column(Text, nullable=True)            # JSON list of strings
    education = Column(Text, nullable=True)
    experience_summary = Column(Text, nullable=True)
    target_roles = Column(Text, nullable=True)      # JSON list of strings

    created_at = Column(DateTime, default=datetime.utcnow)

    matches = relationship("JobMatch", back_populates="profile")


class Job(Base):
    __tablename__ = "jobs"
    # Dedup key: same source + external id should not be inserted twice.
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_job_source_external"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True, default="simplify-newgrad")
    external_id = Column(String, index=True, nullable=True)

    company = Column(String, nullable=True)
    title = Column(String, nullable=True)
    location = Column(String, nullable=True)
    url = Column(String, nullable=True)
    posted_at = Column(String, nullable=True)   # kept as raw text from source
    raw = Column(Text, nullable=True)           # original row/blob for debugging

    created_at = Column(DateTime, default=datetime.utcnow)

    matches = relationship("JobMatch", back_populates="job")
    messages = relationship("Message", back_populates="job")


class JobMatch(Base):
    __tablename__ = "job_matches"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id"), index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True)

    score = Column(Float, default=0.0)
    reasons = Column(Text, nullable=True)  # human-readable why-it-matched

    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile", back_populates="matches")
    job = relationship("Job", back_populates="matches")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, default=DEMO_USER_ID)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True, nullable=True)

    # "connection_request" | "follow_up"
    message_type = Column(String, default="connection_request")
    content = Column(Text, nullable=True)

    # Approval workflow: draft -> approved/rejected -> sent (manual).
    status = Column(String, default="draft", index=True)

    # Real-world result after the user manually sent the message. One of
    # OUTCOMES (or NULL if no outcome reported yet). This is the CRM signal
    # that closes the loop on outreach.
    outcome = Column(String, nullable=True, index=True)

    # Lightweight follow-up tracking (additive columns — see db.py migrations).
    # follow_up_status is one of FOLLOW_UP_STATUSES; follow_up_due_date is a
    # plain ISO date string the user picks (kept as text for SQLite simplicity).
    follow_up_status = Column(String, nullable=True, index=True)
    follow_up_due_date = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    job = relationship("Job", back_populates="messages")
    events = relationship("OutreachEvent", back_populates="message")


class OutreachEvent(Base):
    __tablename__ = "outreach_events"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), index=True)

    # "approved" | "rejected" | "edited" | "copied" | "marked_sent"
    event_type = Column(String, index=True)
    note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    message = relationship("Message", back_populates="events")
