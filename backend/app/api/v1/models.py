"""
Zentar Intelligence — Models & Providers API Routes

List and manage AI models and providers.
"""

from typing import Optional

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.schemas import APIResponse
from app.services.ai_service import provider_registry

router = APIRouter(prefix="/models", tags=["Models & Providers"])


@router.get("/providers", response_model=APIResponse)
async def list_providers(
    user_id: str = Depends(get_current_user),
):
    """List all registered AI providers and their status."""
    providers = provider_registry.list_providers()
    return APIResponse(data={"providers": providers})


@router.get("/providers/{provider_name}/models", response_model=APIResponse)
async def list_provider_models(
    provider_name: str,
    user_id: str = Depends(get_current_user),
):
    """List available models for a specific provider."""
    provider = provider_registry.get_provider(provider_name)
    if not provider:
        return APIResponse(
            success=False,
            message=f"Provider '{provider_name}' not found",
            data={"models": []},
        )

    models = await provider.list_models()
    return APIResponse(data={"models": models})


@router.get("/available", response_model=APIResponse)
async def list_available_models(
    user_id: str = Depends(get_current_user),
):
    """List all available models from all configured providers."""
    all_models = []
    for provider_name in ["openai", "anthropic", "gemini", "deepseek"]:
        provider = provider_registry.get_provider(provider_name)
        if provider and provider.is_configured():
            models = await provider.list_models()
            all_models.extend(models)

    return APIResponse(data={"models": all_models})
