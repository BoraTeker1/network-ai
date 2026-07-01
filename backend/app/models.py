"""SQLAlchemy ORM models for Network AI.

Tables: profiles, jobs, job_matches, messages, outreach_events.
v1 has no auth, so we hardcode a single demo user.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
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

# Legacy single-user id. Rows created before auth landed belong to this id and
# are invisible to real accounts (scripts/create_user.py --claim-demo-data can
# reassign them). New rows ALWAYS carry an explicit authenticated user id.
DEMO_USER_ID = "demo-user"

# Subscription plans. Feature gates live in services/plans.py.
PLANS = ("free", "pro", "admin")


class User(Base):
    """A real account. Passwords are scrypt-hashed (services/passwords.py) —
    plaintext is never stored, logged, or returned."""

    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)   # uuid4 hex
    email = Column(String, unique=True, index=True, nullable=False)  # lowercased
    password_hash = Column(String, nullable=False)
    plan = Column(String, default="free", nullable=False)  # one of PLANS
    created_at = Column(DateTime, default=datetime.utcnow)


class AuthSession(Base):
    """Opaque server-side session. We store the SHA-256 of the token — a DB
    leak alone can't be replayed as a cookie."""

    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)

# Controlled vocabularies for the AI outreach layer (kept here so routers /
# services share one source of truth).
OUTREACH_GOALS = (
    "advice",
    "referral",
    "recruiter_intro",
    "hiring_manager_intro",
    "founder_intro",
)
CONTACT_TYPES = (
    "recruiter",
    "technical_recruiter",
    "hiring_manager",
    "engineer",
    "alumni",
    "founder",
)
# Email approval workflow (mirrors the manual-message workflow; never auto-sends).
EMAIL_STATUSES = (
    "draft",
    "approved",
    "rejected",
    "copied",
    "sent_manual",
    "sent_via_gmail",
)

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

# Momentum (Vibe Mode gamification). Points reward *quality* progress — real
# milestones the user manually confirms — never volume, bulk, or scraping.
# "tracked_no_points" lets a neutral outcome (ignored/rejected/connected) be
# logged with zero points and zero shame.
MOMENTUM_EVENT_TYPES = (
    "draft_approved",
    "copied",
    "sent_manual",
    "follow_up_completed",
    "person_met",
    "reply_received",
    "referral_received",
    "interview_received",
    "tracked_no_points",
)


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)

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

    # ----- Richer normalized fields (additive; populated by newer adapters such
    # as the newgrad-jobs.com source — older Simplify rows simply leave them
    # NULL). See db.run_lightweight_migrations() for the SQLite ADD COLUMNs. -----
    employment_type = Column(String, nullable=True)   # Full-time / Internship / ...
    work_mode = Column(String, nullable=True)         # Onsite / Remote / Hybrid
    salary_range = Column(String, nullable=True)      # e.g. "$57K/yr - $109K/yr"
    level = Column(String, nullable=True)             # e.g. "Entry Level" / "New Grad"
    description = Column(Text, nullable=True)
    responsibilities = Column(Text, nullable=True)    # JSON list of strings
    qualifications = Column(Text, nullable=True)      # JSON list of strings
    benefits = Column(Text, nullable=True)            # JSON list of strings
    # source_url is the listing/detail page we discovered the job on; url +
    # external_apply_url hold the honest apply destination (may be an aggregator,
    # so we never *claim* it is the official company ATS unless it clearly is).
    source_url = Column(String, nullable=True)
    external_apply_url = Column(String, nullable=True)
    is_closed = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    discovered_at = Column(DateTime, default=datetime.utcnow)

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
    user_id = Column(String, index=True, nullable=False)
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

    # ----- Outreach-copilot context (additive; populated by /outreach/save-draft
    # for Turkey→remote/EU drafts that have NO legacy Job row). Job-linked messages
    # leave these NULL and fall back to the linked Job's company/title. This is how
    # the stateless Opportunities→Outreach flow becomes a tracked pipeline item. --
    company = Column(String, nullable=True)
    title = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    channel = Column(String, nullable=True)          # "email" | "linkedin"
    language = Column(String, nullable=True)          # "en" | "tr"
    job_url = Column(String, nullable=True)
    contact_name = Column(String, nullable=True)
    contact_title = Column(String, nullable=True)
    opportunity_id = Column(
        Integer, ForeignKey("opportunities.id"), index=True, nullable=True
    )

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


# ----- AI outreach layer (additive tables; create_all handles them) -----


class Goal(Base):
    """The user's current job-search / outreach goal. Feeds email generation."""

    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)

    target_role = Column(String, nullable=True)
    target_location = Column(String, nullable=True)
    target_company_type = Column(String, nullable=True)
    outreach_goal = Column(String, nullable=True)        # one of OUTREACH_GOALS
    tone_preference = Column(String, nullable=True)
    max_contacts_per_company = Column(Integer, default=3)
    preferred_contact_types = Column(Text, nullable=True)  # JSON list of CONTACT_TYPES
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Contact(Base):
    """A person the user may reach out to. Manually added or, later, returned by
    a COMPLIANT discovery provider. Contact info is never scraped or invented."""

    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True, nullable=True)

    name = Column(String, nullable=True)
    title = Column(String, nullable=True)
    company = Column(String, nullable=True)
    email = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    contact_type = Column(String, nullable=True)          # one of CONTACT_TYPES
    email_confidence = Column(Integer, nullable=True)      # 0-100, provider-supplied
    source = Column(String, default="manual")             # "manual" | "hunter" | "pdl"
    source_note = Column(Text, nullable=True)
    why_relevant = Column(Text, nullable=True)
    risk_note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job")


class Meeting(Base):
    """A person the user actually MET — at an event, online, or via an intro.

    This is the core "presence" signal: it turns showing up into a tracked
    relationship. Logged manually by the user (never scraped/auto-detected), it
    powers the presence funnel and earns Momentum. Distinct from Contact, which
    is "someone to reach out to" — a Meeting is "someone I already connected with."
    """

    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True, nullable=True)

    name = Column(String, nullable=False)
    title = Column(String, nullable=True)
    company = Column(String, nullable=True)
    where_met = Column(String, nullable=True)       # event/place, e.g. "JS Conf NY"
    met_on = Column(String, nullable=True)          # ISO date (YYYY-MM-DD)
    contact_type = Column(String, nullable=True)    # one of CONTACT_TYPES
    linkedin_url = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    followed_up = Column(Boolean, default=False)    # did the user follow up yet?

    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job")


class EmailDraft(Base):
    """An AI- or template-generated email draft awaiting user review/approval.

    Nothing is ever sent automatically — status moves only on explicit user
    action, exactly like the Message approval workflow."""

    __tablename__ = "email_drafts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), index=True, nullable=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), index=True, nullable=True)
    goal_id = Column(Integer, ForeignKey("goals.id"), index=True, nullable=True)

    subject = Column(String, nullable=True)
    body = Column(Text, nullable=True)
    message_type = Column(String, default="outreach_email")
    tone = Column(String, nullable=True)
    personalization_notes = Column(Text, nullable=True)
    quality_checklist = Column(Text, nullable=True)        # JSON
    risk_checklist = Column(Text, nullable=True)           # JSON
    llm_used = Column(Boolean, default=False)

    status = Column(String, default="draft", index=True)   # one of EMAIL_STATUSES
    outcome = Column(String, nullable=True, index=True)    # reuse OUTCOMES
    follow_up_status = Column(String, nullable=True, index=True)
    follow_up_due_date = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    job = relationship("Job")
    contact = relationship("Contact")
    goal = relationship("Goal")


class MomentumEvent(Base):
    """A single awarded Momentum event (Vibe Mode gamification).

    Each (subject_type, subject_id, event_type) can be awarded only once — the
    unique constraint prevents double-counting when the user clicks the same
    outcome twice. Points reward confirmed, quality progress, never volume."""

    __tablename__ = "momentum_events"
    __table_args__ = (
        UniqueConstraint(
            "subject_type", "subject_id", "event_type", name="uq_momentum_once"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)

    # What the event was awarded for, e.g. ("message", 12) or ("email", 3).
    subject_type = Column(String, index=True, nullable=True)
    subject_id = Column(Integer, index=True, nullable=True)

    event_type = Column(String, index=True)   # one of MOMENTUM_EVENT_TYPES
    points = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)


# ----- Usage tracking (plan gates) ---------------------------------------------


class UsageEvent(Base):
    """One gated action by one user (e.g. an outreach draft). services/plans.py
    counts these against the user's plan limits. Content is never stored here."""

    __tablename__ = "usage_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    action = Column(String, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# ----- Audit log (production-readiness layer) ---------------------------------
# Small, append-only record of security-relevant events. NEVER stores resume
# text, message bodies, passwords, tokens, API keys, or payment details — only
# event names, an optional user id, an optional client IP, and a short note.

AUDIT_EVENTS = (
    "signup",
    "login_success",
    "login_failed",
    "logout",
    "plan_changed",
    "rate_limited",
    "upload_rejected",
)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=True)   # None for anon events
    event = Column(String, index=True)                     # one of AUDIT_EVENTS
    ip = Column(String, nullable=True)
    note = Column(Text, nullable=True)                     # short, non-sensitive
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# ----- Curated Turkey + Remote/EU opportunity feed (additive, isolated table) --
# Deliberately SEPARATE from Job (which powers the US matcher/messages flows). An
# opportunity is a curated/compliant listing for Turkish junior engineers that
# feeds the bilingual outreach copilot. No scraping of protected sites — sources
# are curated samples, public job APIs, company pages, and manual JSON import.

# Where the role sits, from a Turkey-based junior's perspective.
OPP_TARGET_REGIONS = ("turkey", "europe", "remote", "global", "unknown")
OPP_SENIORITY_LEVELS = ("internship", "new_grad", "junior", "mid", "senior", "unknown")
OPP_REMOTE_POLICIES = ("remote", "hybrid", "onsite", "unknown")
# Conservative eligibility labels for a Turkey-based candidate.
TURKEY_APPLICABILITY_LABELS = (
    "Strong fit for Turkey-based candidates",
    "Possibly eligible",
    "Unclear",
    "Probably not eligible",
)


class Opportunity(Base):
    __tablename__ = "opportunities"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_opp_source_external"),
    )

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, index=True, default="curated-sample")  # provider:token (dedup scope)
    external_id = Column(String, index=True, nullable=True)
    source_provider = Column(String, index=True, nullable=True)     # lever/greenhouse/ashby/arbeitnow/sample/manual
    source_confidence = Column(String, index=True, nullable=True)   # official_ats/public_api/manual_curated/sample_demo/unknown

    company = Column(String, nullable=True)
    title = Column(String, nullable=True)
    location = Column(String, nullable=True)
    url = Column(String, nullable=True)            # apply / listing URL (verbatim)
    source_url = Column(String, nullable=True)

    target_region = Column(String, index=True, default="unknown")   # OPP_TARGET_REGIONS
    seniority_level = Column(String, index=True, default="unknown")  # OPP_SENIORITY_LEVELS
    job_function = Column(String, index=True, nullable=True)         # software_engineering/other
    remote_policy = Column(String, default="unknown")               # OPP_REMOTE_POLICIES
    country_scope = Column(String, nullable=True)    # e.g. "EMEA", "Worldwide", "US only"
    accepts_turkey_based = Column(Boolean, nullable=True)  # explicit override if known

    turkey_applicability_label = Column(String, index=True, nullable=True)
    turkey_applicability_reason = Column(Text, nullable=True)

    language_expectation = Column(String, nullable=True)   # e.g. "English"
    work_auth_note = Column(Text, nullable=True)           # only if explicitly stated
    description = Column(Text, nullable=True)
    tags_json = Column(Text, nullable=True)                # JSON list of strings
    raw_source_json = Column(Text, nullable=True)          # original record, for debugging

    date_posted = Column(String, nullable=True)            # raw text from source
    date_seen = Column(DateTime, default=datetime.utcnow, index=True)
    is_sample = Column(Boolean, default=False)             # demo/sample row?

    created_at = Column(DateTime, default=datetime.utcnow)
