"""
Zentar Intelligence — Authentication API Routes

User registration, login, token refresh, and profile management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas import (
    APIResponse,
    AuthLoginRequest,
    AuthRefreshRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
    UserProfileResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=APIResponse[AuthTokenResponse])
async def register(
    request: AuthRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user account."""
    service = AuthService(db)
    user, access_token, refresh_token = await service.register(
        email=request.email,
        password=request.password,
        display_name=request.display_name,
    )
    return APIResponse(
        message="Registration successful",
        data=AuthTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=900,  # 15 minutes
        ),
    )


@router.post("/login", response_model=APIResponse[AuthTokenResponse])
async def login(
    request: AuthLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return tokens."""
    service = AuthService(db)
    user, access_token, refresh_token = await service.login(
        email=request.email,
        password=request.password,
    )
    return APIResponse(
        message="Login successful",
        data=AuthTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=900,
        ),
    )


@router.post("/refresh", response_model=APIResponse[AuthTokenResponse])
async def refresh_token(
    request: AuthRefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh an expired access token."""
    service = AuthService(db)
    access_token, refresh_token = await service.refresh_token(
        refresh_token=request.refresh_token,
    )
    return APIResponse(
        data=AuthTokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=900,
        ),
    )


@router.get("/profile", response_model=APIResponse[UserProfileResponse])
async def get_profile(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's profile."""
    service = AuthService(db)
    user = await service.get_profile(user_id)
    return APIResponse(data=UserProfileResponse.model_validate(user))


@router.put("/profile", response_model=APIResponse[UserProfileResponse])
async def update_profile(
    display_name: str = None,
    avatar_url: str = None,
    bio: str = None,
    theme: str = None,
    language: str = None,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's profile."""
    service = AuthService(db)
    kwargs = {k: v for k, v in locals().items() if v is not None and k not in ("user_id", "db")}
    user = await service.update_profile(user_id, **kwargs)
    return APIResponse(
        message="Profile updated",
        data=UserProfileResponse.model_validate(user),
    )
