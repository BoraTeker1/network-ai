"""Profile endpoints (per authenticated user).

Pasting a resume creates the user's profile the first time and updates it on
every subsequent paste (no duplicates).
"""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_user
from ..models import Profile, User
from ..schemas import ProfileUpdateIn, ResumeTextIn
from ..services import audit, events, plans
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


def _load_list(raw: str | None) -> list:
    """Decode a JSON-encoded list column, tolerating legacy/corrupt values."""
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def _serialize(profile: Profile) -> dict:
    """Convert a Profile row into a clean JSON-friendly dict.

    The raw resume text is deliberately never returned — the UI only needs to
    know that one exists, plus the filename/date for the "last CV update" card.
    """
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "skills": _load_list(profile.skills),
        "education": profile.education,
        "experience_summary": profile.experience_summary,
        "target_roles": _load_list(profile.target_roles),
        "seniority": profile.seniority,
        "preferred_locations": _load_list(profile.preferred_locations),
        "work_models": _load_list(profile.work_models),
        "priorities": _load_list(profile.priorities),
        "has_resume": bool(profile.raw_resume),
        "resume_filename": profile.resume_filename,
        "resume_updated_at": (
            profile.resume_updated_at.isoformat() if profile.resume_updated_at else None
        ),
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
    }


def _save_profile_from_text(
    db: Session,
    resume_text: str,
    user_id: str,
    filename: str | None = None,
) -> dict:
    """Parse resume text and upsert the user's profile.

    Shared by both the paste-text and file-upload endpoints so parsing/upsert
    logic lives in exactly one place. `filename` is None for pasted text.
    Raises HTTP 400 on empty text.
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
    # Provenance for the "last CV update" card. Preferences are left untouched —
    # a re-upload must never wipe what the user set by hand.
    profile.resume_filename = (filename or "").strip()[:200] or None
    profile.resume_updated_at = datetime.utcnow()

    db.commit()
    db.refresh(profile)
    events.track(db, "resume_uploaded", user_id=user_id,
                 note=f"{len(parsed['skills'])} skills extracted")
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

    return _save_profile_from_text(db, resume_text, user.id, filename=file.filename)


@router.get("")
def get_profile(db: Session = Depends(get_db), user: User = Depends(require_user)):
    """Return the current user's saved profile."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile is None:
        raise HTTPException(status_code=404, detail="No profile saved yet")
    return _serialize(profile)


def _clean_list(items: list[str], *, max_item_chars: int = 80) -> list[str]:
    """Strip, drop empties, dedupe case-insensitively, keep first-seen order."""
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        s = (item or "").strip()[:max_item_chars]
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out


def _dedupe(items: list[str]) -> list[str]:
    """Drop duplicates from an enum-valued list, preserving order (= rank)."""
    out: list[str] = []
    for item in items:
        if item not in out:
            out.append(item)
    return out


@router.put("")
def update_profile(
    payload: ProfileUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    """Edit the structured profile fields directly (skills chips, target roles,
    summary, job-search preferences). Creates an empty profile if none exists
    yet, so a user can build one by hand without uploading a resume. The raw
    resume text is untouched."""
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)

    if payload.skills is not None:
        profile.skills = json.dumps(_clean_list(payload.skills))
    if payload.target_roles is not None:
        profile.target_roles = json.dumps(_clean_list(payload.target_roles))
    if payload.experience_summary is not None:
        profile.experience_summary = payload.experience_summary.strip() or None

    # Preferences. Pydantic already rejected unknown values; dedupe here so the
    # stored lists stay clean (and priorities stay a ranked list, order intact).
    if payload.seniority is not None:
        profile.seniority = payload.seniority
    if payload.preferred_locations is not None:
        profile.preferred_locations = json.dumps(_clean_list(payload.preferred_locations))
    if payload.work_models is not None:
        profile.work_models = json.dumps(_dedupe(payload.work_models))
    if payload.priorities is not None:
        profile.priorities = json.dumps(_dedupe(payload.priorities))

    db.commit()
    db.refresh(profile)
    return _serialize(profile)
