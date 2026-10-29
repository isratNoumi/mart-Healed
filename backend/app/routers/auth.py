import time

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..clock import utc_now
from ..config import settings
from ..database import get_db
from ..dependencies import get_optional_user
from ..models import User
from ..schemas import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from ..services.auth_service import (
    MAX_LOGIN_QUEUE_WAIT_SECONDS,
    SECURE_COOKIES,
    SESSION_COOKIE,
    SESSION_LIFETIME,
    clear_failed_logins,
    create_session,
    delete_session,
    hash_password,
    is_registration_rate_limited,
    reserve_login_slot,
    record_failed_login,
    record_registration_attempt,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        httponly=True,
        samesite="lax",
        secure=SECURE_COOKIES,
        path="/",
    )


REGISTRATION_FAILED = "We couldn't create an account with those details. If you already have an account, try signing in."
TOO_MANY_REGISTRATIONS = "Too many sign-up attempts. Please try again in 15 minutes."


def client_id(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    # Only honour X-Forwarded-For when the direct peer is an explicitly trusted
    # reverse proxy; otherwise the header is attacker-controlled.
    if peer in settings.trusted_proxy_set:
        forwarded = request.headers.get("x-forwarded-for", "")
        hops = [h.strip() for h in forwarded.split(",") if h.strip()]
        # Walk from the right, skipping our own trusted proxies.
        while hops and hops[-1] in settings.trusted_proxy_set:
            hops.pop()
        if hops:
            return hops[-1]
    return peer


def auth_response(user: User | None) -> AuthResponse:
    return AuthResponse(user=UserResponse.model_validate(user, from_attributes=True) if user else None)


@router.post("/register", response_model=AuthResponse, status_code=202)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """Create an account.

    The response is deliberately identical (status, body, headers, and comparable
    timing) whether or not the email is already registered, so this endpoint can't
    be used as an account-existence oracle. No session is issued here; the client
    signs in via ``/api/auth/login`` afterwards, which fails uniformly for unknown
    accounts and wrong passwords.
    """
    client = client_id(request)
    if is_registration_rate_limited(client):
        raise HTTPException(status_code=429, detail=TOO_MANY_REGISTRATIONS)
    # Always pay the hashing cost so timing doesn't reveal whether the email exists.
    password_hash = hash_password(payload.password)
    duplicate = db.query(User).filter(User.email == payload.email).first() is not None
    if not duplicate:
        db.add(
            User(
                first_name=payload.first_name,
                last_name=payload.last_name,
                email=payload.email,
                password_hash=password_hash,
                created_at=utc_now(),
            )
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            duplicate = True
    record_registration_attempt(client, duplicate=duplicate)
    return auth_response(None)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    client = client_id(request)
    # Throttle (bounded delay) instead of hard-blocking: rejecting requests based on
    # failure counts would let anyone lock out a known email, or every user sharing
    # an IP. The delay is applied before the password check so response timing
    # doesn't reveal whether a guess was correct. Throttled attempts are
    # serialized per account (each reserves its own slot), so opening many
    # parallel connections does not multiply guess throughput; if the queue is
    # already saturated the attempt is rejected (429) without checking credentials.
    delay = reserve_login_slot(payload.email, client)
    if delay is None:
        raise HTTPException(
            status_code=429,
            detail="Too many sign-in attempts. Please wait a moment and try again.",
            headers={"Retry-After": str(int(MAX_LOGIN_QUEUE_WAIT_SECONDS))},
        )
    if delay > 0:
        time.sleep(delay)
    user = db.query(User).filter(User.email == payload.email).first()
    if not verify_password(user, payload.password):
        record_failed_login(payload.email, client)
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    clear_failed_logins(payload.email, client)
    token = create_session(db, user)
    db.commit()
    set_session_cookie(response, token)
    return auth_response(user)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
):
    delete_session(db, session_token)
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax", secure=SECURE_COOKIES)


@router.get("/me", response_model=AuthResponse)
def current_user(user: User | None = Depends(get_optional_user)):
    return auth_response(user)
