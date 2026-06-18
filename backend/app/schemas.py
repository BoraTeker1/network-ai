"""Pydantic schemas for request/response bodies.

Skeleton level — just enough to make the API browsable and typed.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


# ----- Profile -----

class ResumeTextIn(BaseModel):
    resume_text: str


class ProfileCreate(BaseModel):
    raw_resume: str


class ProfileOut(BaseModel):
    id: int
    user_id: str
    skills: Optional[List[str]] = None
    education: Optional[str] = None
    experience_summary: Optional[str] = None
    target_roles: Optional[List[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ----- Job -----

class JobOut(BaseModel):
    id: int
    source: str
    external_id: Optional[str] = None
    company: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None
    url: Optional[str] = None
    posted_at: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class IngestResult(BaseModel):
    ingested: int
    skipped_duplicates: int
    total_in_db: int


class NewGradIngestIn(BaseModel):
    """Optional knobs for the newgrad-jobs.com ingestion (all have safe defaults)."""

    categories: Optional[List[str]] = None       # default category set if None
    max_per_category: Optional[int] = 15         # conservative cap per category
    request_delay: Optional[float] = None        # seconds between detail fetches


# ----- Job match -----

class JobMatchOut(BaseModel):
    id: int
    job_id: int
    profile_id: int
    score: float
    reasons: Optional[str] = None

    class Config:
        from_attributes = True


# ----- Message -----

class MessageCreate(BaseModel):
    job_id: Optional[int] = None
    message_type: str = "connection_request"


class MessageGenerateIn(BaseModel):
    job_id: int
    contact_name: Optional[str] = None
    contact_title: Optional[str] = None


class MessagePatch(BaseModel):
    draft_text: str


class OutcomeIn(BaseModel):
    outcome: str
    note: Optional[str] = None


class FollowUpIn(BaseModel):
    status: str                       # one of FOLLOW_UP_STATUSES
    due_date: Optional[str] = None    # ISO date string (YYYY-MM-DD), optional


class MessageUpdate(BaseModel):
    content: Optional[str] = None
    status: Optional[str] = None


class MessageOut(BaseModel):
    id: int
    user_id: str
    job_id: Optional[int] = None
    message_type: str
    content: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ----- Goals -----

class GoalIn(BaseModel):
    target_role: Optional[str] = None
    target_location: Optional[str] = None
    target_company_type: Optional[str] = None
    outreach_goal: Optional[str] = None
    tone_preference: Optional[str] = None
    max_contacts_per_company: Optional[int] = 3
    preferred_contact_types: Optional[List[str]] = None
    notes: Optional[str] = None


# ----- Contacts -----

class ContactManualIn(BaseModel):
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    linkedin_url: Optional[str] = None
    contact_type: Optional[str] = None
    email_confidence: Optional[int] = None
    source_note: Optional[str] = None
    job_id: Optional[int] = None


class DiscoverIn(BaseModel):
    job_id: Optional[int] = None
    goal_id: Optional[int] = None
    contact_type: str = "recruiter"
    max_results: int = 5


# ----- Emails -----

class EmailDraftIn(BaseModel):
    job_id: int
    contact_id: int
    goal_id: Optional[int] = None
    tone: Optional[str] = "warm_low_pressure"


class EmailPatchIn(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    outcome: Optional[str] = None
    follow_up_status: Optional[str] = None
    follow_up_due_date: Optional[str] = None


class GmailSendIn(BaseModel):
    confirm_send: bool = False


# ----- Next Move AI -----

class NextMoveIn(BaseModel):
    # The reply the user RECEIVED, pasted in manually (never auto-read).
    reply_text: str
    # Optional links to existing pipeline data for richer context + a target to
    # update when the user confirms an outcome.
    job_id: Optional[int] = None
    contact_id: Optional[int] = None
    message_id: Optional[int] = None
    email_id: Optional[int] = None


# ----- Generic -----

class StatusResponse(BaseModel):
    status: str
