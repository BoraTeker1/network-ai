"""Pydantic schemas for request/response bodies.

Input fields carry max_length limits so oversized pastes are rejected at the
edge (422) instead of reaching parsers, the DB, or an LLM prompt.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

# Shared input-size ceilings (characters). Generous for real use, hostile to abuse.
MAX_RESUME_CHARS = 60_000
MAX_JD_CHARS = 20_000
MAX_BODY_CHARS = 10_000
MAX_SUBJECT_CHARS = 300
MAX_NOTE_CHARS = 2_000
MAX_NAME_CHARS = 300
MAX_EMAIL_CHARS = 320
MAX_URL_CHARS = 1_000


# ----- Auth -----

class SignupIn(BaseModel):
    email: str = Field(min_length=3, max_length=MAX_EMAIL_CHARS)
    password: str = Field(min_length=8, max_length=200)


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=MAX_EMAIL_CHARS)
    password: str = Field(min_length=1, max_length=200)


# ----- Profile -----

class ResumeTextIn(BaseModel):
    resume_text: str = Field(max_length=MAX_RESUME_CHARS)


class ProfileCreate(BaseModel):
    raw_resume: str = Field(max_length=MAX_RESUME_CHARS)


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


# ----- Message -----

class MessagePatch(BaseModel):
    draft_text: str = Field(max_length=MAX_BODY_CHARS)


class OutcomeIn(BaseModel):
    outcome: str = Field(max_length=50)
    note: Optional[str] = Field(None, max_length=MAX_NOTE_CHARS)


class FollowUpIn(BaseModel):
    status: str = Field(max_length=50)               # one of FOLLOW_UP_STATUSES
    due_date: Optional[str] = Field(None, max_length=20)  # ISO date (YYYY-MM-DD)


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
    target_role: Optional[str] = Field(None, max_length=MAX_NAME_CHARS)
    target_location: Optional[str] = Field(None, max_length=MAX_NAME_CHARS)
    target_company_type: Optional[str] = Field(None, max_length=MAX_NAME_CHARS)
    outreach_goal: Optional[str] = Field(None, max_length=50)
    tone_preference: Optional[str] = Field(None, max_length=50)
    max_contacts_per_company: Optional[int] = 3
    preferred_contact_types: Optional[List[str]] = None
    notes: Optional[str] = Field(None, max_length=MAX_NOTE_CHARS)


# ----- Contacts -----

class ContactManualIn(BaseModel):
    name: str = Field(max_length=MAX_NAME_CHARS)
    title: Optional[str] = Field(None, max_length=MAX_NAME_CHARS)
    company: Optional[str] = Field(None, max_length=MAX_NAME_CHARS)
    email: Optional[str] = Field(None, max_length=MAX_EMAIL_CHARS)
    linkedin_url: Optional[str] = Field(None, max_length=MAX_URL_CHARS)
    contact_type: Optional[str] = Field(None, max_length=50)
    email_confidence: Optional[int] = None
    source_note: Optional[str] = Field(None, max_length=MAX_NOTE_CHARS)
    job_id: Optional[int] = None


class DiscoverIn(BaseModel):
    job_id: Optional[int] = None
    goal_id: Optional[int] = None
    contact_type: str = "recruiter"
    max_results: int = 5


# ----- Emails -----

class EmailDraftIn(BaseModel):
    opportunity_id: int
    contact_id: int
    goal_id: Optional[int] = None
    tone: Optional[str] = "warm_low_pressure"


class EmailPatchIn(BaseModel):
    subject: Optional[str] = Field(None, max_length=MAX_SUBJECT_CHARS)
    body: Optional[str] = Field(None, max_length=MAX_BODY_CHARS)
    outcome: Optional[str] = Field(None, max_length=50)
    follow_up_status: Optional[str] = Field(None, max_length=50)
    follow_up_due_date: Optional[str] = Field(None, max_length=20)


class GmailSendIn(BaseModel):
    confirm_send: bool = False


# ----- LinkedIn -----

class LinkedInDraftIn(BaseModel):
    opportunity_id: int
    contact_id: int
    goal_id: Optional[int] = None
    kind: str = "connection"          # "connection" (300-char note) | "dm"
    tone: Optional[str] = "warm_low_pressure"


# ----- Next Move AI -----

class NextMoveIn(BaseModel):
    # The reply the user RECEIVED, pasted in manually (never auto-read).
    reply_text: str = Field(max_length=MAX_BODY_CHARS)
    # Optional links to existing pipeline data for richer context + a target to
    # update when the user confirms an outcome.
    job_id: Optional[int] = None
    contact_id: Optional[int] = None
    message_id: Optional[int] = None
    email_id: Optional[int] = None


# ----- Paste-a-JD bilingual outreach (Turkey → remote/EU wedge) -----

class OutreachContactIn(BaseModel):
    name: Optional[str] = Field(None, max_length=MAX_NAME_CHARS)
    title: Optional[str] = Field(None, max_length=MAX_NAME_CHARS)
    company: Optional[str] = Field(None, max_length=MAX_NAME_CHARS)


class OutreachPasteIn(BaseModel):
    # The job description the user pasted in manually (never scraped).
    jd_text: str = Field(max_length=MAX_JD_CHARS)
    contact: OutreachContactIn = OutreachContactIn()
    language: str = "en"             # "en" | "tr"
    channel: str = "email"           # "email" | "linkedin"
    tone: Optional[str] = "warm_low_pressure"

    # Optional explicit company/role (else inferred from the pasted JD).
    company: Optional[str] = Field(None, max_length=MAX_NAME_CHARS)
    role: Optional[str] = Field(None, max_length=MAX_NAME_CHARS)

    # Remote/EU + visa/timezone framing (all opt-in; nothing is invented).
    target_region: Optional[str] = Field(None, max_length=20)  # remote|europe|global|turkey
    based_in: Optional[str] = Field("Turkey", max_length=100)
    timezone_overlap: Optional[str] = Field(None, max_length=200)
    work_authorization_note: Optional[str] = Field(None, max_length=500)  # user text only
    include_location_line: bool = False
    include_work_auth_line: bool = False
    skill_highlight: Optional[str] = Field(None, max_length=500)  # optional override line


class OutreachSaveIn(BaseModel):
    """Save a generated outreach draft as a tracked pipeline item.

    Reuses the Message model + its manual approval/outcome/follow-up workflow.
    Nothing is ever sent — this only persists the reviewed draft so the user can
    revisit, copy, mark-sent-manually, mark-replied, and follow up.
    """

    body: str = Field(max_length=MAX_BODY_CHARS)
    subject: Optional[str] = Field(None, max_length=MAX_SUBJECT_CHARS)
    company: Optional[str] = Field(None, max_length=MAX_NAME_CHARS)
    role: Optional[str] = Field(None, max_length=MAX_NAME_CHARS)
    channel: str = Field("email", max_length=20)      # "email" | "linkedin"
    language: str = Field("en", max_length=10)        # "en" | "tr"
    opportunity_id: Optional[int] = None   # source opportunity, if drafted from one
    job_url: Optional[str] = Field(None, max_length=MAX_URL_CHARS)
    contact_name: Optional[str] = Field(None, max_length=MAX_NAME_CHARS)
    contact_title: Optional[str] = Field(None, max_length=MAX_NAME_CHARS)
    status: str = Field("copied", max_length=30)      # initial pipeline status


# ----- Opportunities (curated Turkey + remote/EU feed) -----

class OpportunityImportIn(BaseModel):
    # Permissive: accepts raw curated/company-page records pasted as JSON.
    jobs: List[dict]
    source: Optional[str] = "manual-import"
    is_sample: bool = False


class LabelFeedbackIn(BaseModel):
    verdict: str = Field(max_length=10)  # "right" | "wrong"
    reason: Optional[str] = Field(None, max_length=MAX_NOTE_CHARS)


# ----- Product events (validation sprint) -----

class EventIn(BaseModel):
    event: str = Field(max_length=50)  # one of models.PRODUCT_EVENTS
    note: Optional[str] = Field(None, max_length=MAX_NOTE_CHARS)


# ----- Generic -----

class StatusResponse(BaseModel):
    status: str
