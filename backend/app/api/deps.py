from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.config import settings
from app.core.database import get_db
from app.models.models import User
from app.core.security import get_password_hash

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
)

# ── Shared token-decode helper ─────────────────────────────────────────────

def _decode_token(token: Optional[str], db: Session) -> Optional[User]:
    """
    Decode a JWT bearer token and return the matching User, or None on any
    failure (missing token, invalid signature, expired, unknown user).
    Does NOT raise — callers decide how to handle None.
    """
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if not email:
            return None
        return db.query(User).filter(User.email == email).first()
    except JWTError:
        return None


# ── Protected dependency (401 on missing/invalid token) ───────────────────

def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
) -> User:
    """
    Dependency for protected endpoints.
    Raises HTTP 401 if the token is absent, invalid, or does not match any user.
    """
    user = _decode_token(token, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# ── Optional user (returns None instead of raising) ───────────────────────

def get_optional_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
) -> Optional[User]:
    """
    Dependency for endpoints that allow unauthenticated access but behave
    differently when a valid user is present (e.g., the public /verify endpoint).
    Returns the User if a valid token is supplied, otherwise None.
    """
    return _decode_token(token, db)


# ── Explicit demo/guest user (for public demo endpoints only) ─────────────

def get_demo_user(db: Session = Depends(get_db)) -> User:
    """
    Returns a persistent guest/demo user.
    Only inject this dependency on endpoints that are explicitly intended to be
    publicly accessible without authentication (e.g., a sandboxed demo route).
    Do NOT use as a silent fallback for protected endpoints.
    """
    guest_email = "guest@qoaas-platform.com"
    user = db.query(User).filter(User.email == guest_email).first()
    if user is None:
        user = User(
            email=guest_email,
            hashed_password=get_password_hash("guest_password_1337"),
            role="business_analyst",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
