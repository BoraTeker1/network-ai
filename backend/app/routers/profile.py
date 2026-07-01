"""Profile endpoints (per authenticated user).

Pasting a resume creates the user's profile the first time and updates it on
every subsequent paste (no duplicates).
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_user
from ..models import Profile, User
from ..schemas import ResumeTextIn
from ..services import audit, plans
from ..services.rate_limit import rate_limit
from ..services.resume_parser import parse_resume
from ..services.resume_file import (
    MAX_FILE_BYTES,
    ResumeFileError,
    extract_text_from_file,
)

router = APIRouter(prefix="/profile", tags=["profile"])

# Content types browsers commonly send for PDF/DOCX. octet-stream is allowed as
# a fallback (browsers vary); the extension check in resume_file.py stays
# authoritative and the parsers only ever *read* the bytes.
ALLOWED_UPLOAD_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",
}


def _serialize(profile: Profile) -> dict:
    """Convert a Profile row into a clean JSON-friendly dict."""
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "skills": json.loads(profile.skills) if profile.skills else [],
        "education": profile.education,
        "experience_summary": profile.experience_summary,
        "target_roles": json.loads(profile.target_roles) if profile.target_roles else [],
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
    }


def _save_profile_from_text(db: Session, resume_text: str, user_id: str) -> dict:
    """Parse resume text and upsert the user's profile.

    Shared by both the paste-text and file-upload endpoints so parsing/upsert
    logic lives in exactly one place. Raises HTTP 400 on empty text.
    """
    resume_text = (resume_text or "").strip()
    if not resume_text:
        raise HTTPException(status_code=400, detail="resume_text must not be empty")

    parsed = parse_resume(resume_text)

    # Upsert: reuse the existing demo-user profile if present.
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if profile is None:
        profile = Profile(user_id=user_id)
        db.add(profile)

    profile.raw_resume = resume_text
    profile.skills = json.dumps(parsed["skills"])
    profile.experience_summary = parsed["experience_summary"]

    db.commit()
    db.refresh(profile)
    return _serialize(profile)


@router.post("/resume-text")
def save_resume_text(
    payload: ResumeTextIn,
    db: Session = Depends(get_db),
    _rl: None = Depends(rate_limit("resume_upload")),
    user: User = Depends(plans.enforce_limit("resume_upload")),
):
    """Save/replace the user's resume and extract a simple profile."""
    return _save_profile_from_text(db, payload.resume_text, user.id)


@router.post("/resume-file")
async def save_resume_file(
    request: Request,
    file: UploadFile | None = None,
    db: Session = Depends(get_db),
    _rl: None = Depends(rate_limit("resume_upload")),
    user: User = Depends(plans.enforce_limit("resume_upload")),
):
    """Upload a .pdf or .docx resume, extract its text locally, then reuse the
    exact same parse/upsert path as /resume-text.

    Errors: no file / unsupported type / empty / unreadable → 400; oversized → 413.
    Rejections are audit-logged (filename extension only — never file contents).
    """
    ip = request.client.host if request.client else None

    def _reject(status: int, detail: str) -> HTTPException:
        note = (file.filename or "")[-20:] if file else "no file"
        audit.log(db, "upload_rejected", ip=ip, note=note)
        return HTTPException(status_code=status, detail=detail)

    if file is None:
        raise _reject(400, "No file provided.")

    if file.content_type and file.content_type not in ALLOWED_UPLOAD_CONTENT_TYPES:
        raise _reject(400, "Unsupported file type. Upload a .pdf or .docx resume.")

    # Read at most MAX+1 bytes so an oversized upload is rejected without
    # buffering the whole file, and BEFORE any parsing happens.
    data = await file.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise _reject(
            413,
            f"File too large. Max size is {MAX_FILE_BYTES // (1024 * 1024)} MB.",
        )
    if not data:
        raise _reject(400, "The uploaded file is empty.")

    try:
        resume_text = extract_text_from_file(file.filename, data)
    except ResumeFileError as exc:
        raise _reject(400, str(exc))

    return _save_profile_from_text(db, resume_text, user.id)


@router.get("")
def get_profile(db: Session = Depends(get_db), user: User = Depends(require_user)):
    """Return the current user's saved profile."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="No profile saved yet")
    return _serialize(profile)
