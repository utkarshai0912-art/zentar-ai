"""
Zentar Intelligence — Authentication Service

Handles user registration, login, token management, and OAuth.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_token_pair,
    decode_token,
    generate_api_key,
    hash_password,
    verify_password,
)
from app.models.user import User


class AuthService:
    """Service layer for authentication operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(
        self,
        email: str,
        password: str,
        display_name: str,
    ) -> Tuple[User, str, str]:
        """Register a new user and return (user, access_token, refresh_token)."""
        # Check existing
        result = await self.db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        # Create user
        user = User(
            email=email,
            password_hash=hash_password(password),
            display_name=display_name,
        )
        self.db.add(user)
        await self.db.flush()

        # Generate tokens
        access_token, refresh_token = create_token_pair(user.id)
        return user, access_token, refresh_token

    async def login(
        self,
        email: str,
        password: str,
    ) -> Tuple[User, str, str]:
        """Authenticate user and return (user, access_token, refresh_token)."""
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not verify_password(password, user.password_hash):
            # Track failed attempt
            user.failed_login_attempts += 1
            await self.db.flush()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )

        # Reset failed attempts, update last login
        user.failed_login_attempts = 0
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.flush()

        access_token, refresh_token = create_token_pair(user.id)
        return user, access_token, refresh_token

    async def refresh_token(self, refresh_token: str) -> Tuple[str, str]:
        """Refresh an access token using a valid refresh token."""
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        # Verify user still exists and is active
        result = await self.db.execute(
            select(User).where(User.id == payload["sub"])
        )
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or deactivated",
            )

        return create_token_pair(user.id)

    async def get_profile(self, user_id: str) -> User:
        """Get user profile by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    async def update_profile(
        self,
        user_id: str,
        **kwargs,
    ) -> User:
        """Update user profile fields."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        allowed_fields = {
            "display_name", "avatar_url", "bio", "timezone",
            "theme", "language", "preferences",
        }
        for key, value in kwargs.items():
            if key in allowed_fields and value is not None:
                setattr(user, key, value)

        await self.db.flush()
        return user

    async def rotate_api_key(self, user_id: str) -> str:
        """Generate a new API key for the user."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        new_key = generate_api_key()
        user.api_key = new_key
        user.api_key_created_at = datetime.now(timezone.utc)
        await self.db.flush()
        return new_key
