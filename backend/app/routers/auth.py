"""Auth endpoints: signup, login, logout, current user.

Session cookie: HttpOnly + SameSite=Lax + Secure (COOKIE_SECURE env). CSRF
posture: Lax cookie + strict CORS origins + JSON-only mutations. Email
verification and password reset are deliberately deferred for the invite-only
beta (see PRODUCTION_CHECKLIST.md).
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from .. import config
from ..db import get_db
from ..deps import COOKIE_NAME, client_ip, require_user
from ..models import User
from ..schemas import LoginIn, SignupIn
from ..services import audit
from ..services import auth as auth_service
from ..services.rate_limit import rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])


def _serialize(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "plan": user.plan,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _set_session_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        raw_token,
        httponly=True,
        samesite="lax",
        secure=config.cookie_secure(),
        max_age=config.session_ttl_days() * 86400,
        path="/",
    )


@router.post("/signup", status_code=201, dependencies=[Depends(rate_limit("signup", by="ip"))])
def signup(
    payload: SignupIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Create an account and log it in immediately (cookie set)."""
    try:
        user = auth_service.create_user(db, payload.email, payload.password)
    except auth_service.AuthError as exc:
        status = 409 if "already exists" in str(exc) else 400
        raise HTTPException(status_code=status, detail=str(exc))

    _set_session_cookie(response, auth_service.create_session(db, user.id))
    audit.log(db, "signup", user_id=user.id, ip=client_ip(request), note=user.email)
    return _serialize(user)


@router.post("/login", dependencies=[Depends(rate_limit("login", by="ip"))])
def login(
    payload: LoginIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    user = auth_service.authenticate(db, payload.email, payload.password)
    if user is None:
        # Uniform message — never reveal whether the email exists.
        audit.log(
            db, "login_failed", ip=client_ip(request),
            note=auth_service.normalize_email(payload.email),
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")

    _set_session_cookie(response, auth_service.create_session(db, user.id))
    audit.log(db, "login_success", user_id=user.id, ip=client_ip(request))
    return _serialize(user)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    """Idempotent: revokes the session server-side and clears the cookie."""
    token = request.cookies.get(COOKIE_NAME, "")
    if token:
        user = auth_service.get_user_for_token(db, token)
        auth_service.revoke_session(db, token)
        if user is not None:
            audit.log(db, "logout", user_id=user.id, ip=client_ip(request))
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"status": "logged_out"}


@router.get("/me")
def me(user: User = Depends(require_user)):
    return _serialize(user)
