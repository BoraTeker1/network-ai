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


# ----- Generic -----

class StatusResponse(BaseModel):
    status: str
