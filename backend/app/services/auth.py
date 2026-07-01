"""Account + opaque-session management.

Sessions are random tokens stored HASHED (SHA-256) — the raw token exists only
in the user's HttpOnly cookie. Revocation and expiry are enforced server-side.
"""

import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .. import config
from ..models import PLANS, AuthSession, User
from . import passwords

# Deliberately loose (full RFC 5322 is a trap) — just enough to catch typos.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

MIN_PASSWORD_LENGTH = 8


class AuthError(ValueError):
    """User-facing auth validation error (safe to return in a 4xx detail)."""


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def create_user(db: Session, email: str, password: str, plan: str = "free") -> User:
    email = normalize_email(email)
    if not _EMAIL_RE.match(email):
        raise AuthError("Enter a valid email address.")
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if plan not in PLANS:
        raise AuthError(f"Unknown plan '{plan}'.")
    if db.query(User).filter(User.email == email).first() is not None:
        raise AuthError("An account with this email already exists.")

    user = User(
        id=uuid.uuid4().hex,
        email=email,
        password_hash=passwords.hash_password(password),
        plan=plan,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    """Return the user on valid credentials, else None (uniform for wrong
    email vs wrong password — never reveal which)."""
    user = db.query(User).filter(User.email == normalize_email(email)).first()
    if user is None:
        # Burn comparable time so response timing doesn't leak email existence.
        passwords.verify_password(password, passwords.hash_password("timing-pad"))
        return None
    return user if passwords.verify_password(password, user.password_hash) else None


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_session(db: Session, user_id: str) -> str:
    """Create a session and return the RAW token (goes in the cookie only)."""
    raw = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            token_hash=_hash_token(raw),
            user_id=user_id,
            expires_at=datetime.utcnow() + timedelta(days=config.session_ttl_days()),
        )
    )
    db.commit()
    return raw


def get_user_for_token(db: Session, raw_token: str) -> User | None:
    if not raw_token:
        return None
    session = (
        db.query(AuthSession)
        .filter(
            AuthSession.token_hash == _hash_token(raw_token),
            AuthSession.revoked.is_(False),
            AuthSession.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if session is None:
        return None
    return db.query(User).filter(User.id == session.user_id).first()


def revoke_session(db: Session, raw_token: str) -> None:
    """Server-side revocation (idempotent) — deleting the cookie isn't enough."""
    if not raw_token:
        return
    session = (
        db.query(AuthSession)
        .filter(AuthSession.token_hash == _hash_token(raw_token))
        .first()
    )
    if session is not None:
        session.revoked = True
        db.commit()
