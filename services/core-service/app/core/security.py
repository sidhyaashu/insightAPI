"""Core Service — JWT issue/verify/revoke and bcrypt password hashing helpers."""
from __future__ import annotations

import uuid
import secrets
from datetime import datetime, timezone, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def generate_random_token() -> str:
    """Generate a URL-safe random token for email verification and password reset."""
    return secrets.token_urlsafe(32)


def create_access_token(user_id: str, tier: str, role: str = "user") -> str:
    """Issue a short-lived JWT access token (15 min default)."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "tier": tier,
        "role": role,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """Issue a long-lived refresh token. Returns (encoded_token, jti)."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "jti": jti,
        "iat": now,
        "exp": expire,
        "type": "refresh",
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises JWTError on invalid/expired tokens."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
