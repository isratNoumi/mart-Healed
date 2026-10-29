from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .services.auth_service import SESSION_COOKIE, get_session_user


def get_optional_user(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    db: Session = Depends(get_db),
) -> User | None:
    return get_session_user(db, session_token)


def require_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    return user
