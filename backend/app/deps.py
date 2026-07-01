"""Shared FastAPI dependencies: authentication + client identity.

Wiring convention: private endpoints declare `user: User = Depends(require_user)`
explicitly (grep-able for isolation audits) and scope every query by `user.id`.
"""

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from . import config
from .db import get_db
from .models import User
from .services import auth as auth_service

COOKIE_NAME = "na_session"


def optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Resolve the current user from the session cookie, or None when anonymous."""
    token = request.cookies.get(COOKIE_NAME, "")
    return auth_service.get_user_for_token(db, token)


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    """401 unless a valid, unexpired, unrevoked session cookie is presented."""
    user = optional_user(request, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if user.plan != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def client_ip(request: Request) -> str:
    """Client IP for rate limiting / audit. X-Forwarded-For is honored ONLY
    when TRUST_PROXY=true (first hop), otherwise it's trivially spoofable."""
    if config.trust_proxy():
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
