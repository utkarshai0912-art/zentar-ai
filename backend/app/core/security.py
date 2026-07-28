"""
Zentar Intelligence — Security & Authentication

JWT token management, password hashing, and security utilities.
Uses bcrypt for password hashing and PyJWT for token handling.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from app.core.config import get_settings

settings = get_settings()
security_scheme = HTTPBearer(auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with a generated salt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(
    subject: str,
    extra_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token with short expiry."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + expires_delta,
        "iss": settings.JWT_ISSUER,
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(subject: str) -> str:
    """Create a JWT refresh token with longer expiry."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        "iss": settings.JWT_ISSUER,
        "jti": str(uuid.uuid4()),
        "type": "refresh",
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_token_pair(subject: str) -> Tuple[str, str]:
    """Create an access + refresh token pair."""
    return (
        create_access_token(subject),
        create_refresh_token(subject),
    )


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a JWT token.
    Raises HTTPException for expired or invalid tokens.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
        )
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def refresh_access_token(refresh_token: str) -> Tuple[str, str]:
    """Validate a refresh token and issue a new token pair."""
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )
    return create_token_pair(payload["sub"])


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
) -> str:
    """
    Dependency: extracts and validates the current user from the Bearer token.
    Returns the user ID (subject claim).
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    payload = decode_token(credentials.credentials)
    return payload["sub"]


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
) -> Optional[str]:
    """Dependency: returns user ID if authenticated, None otherwise."""
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        return payload["sub"]
    except HTTPException:
        return None


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"zar_{uuid.uuid4().hex}_{uuid.uuid4().hex[:16]}"
