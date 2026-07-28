"""
Zentar Intelligence — API v1 Router Aggregation

Aggregates all v1 API routers under the /api/v1 prefix.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.models import router as models_router
from app.api.v1.agents import router as agents_router
from app.api.v1.mcp import router as mcp_router
from app.api.v1.plugins import router as plugins_router
from app.api.v1.skills import router as skills_router
from app.api.v1.automation import router as automation_router
from app.api.v1.voice import router as voice_router
from app.api.v1.memory_api import router as memory_router
from app.api.v1.admin import router as admin_router
from app.api.v1.marketplace import router as marketplace_router
from app.api.v1.agents_ext import router as ceo_router
from app.api.v1.agents_ext import sales_router
from app.api.v1.agents_ext import custom_router
from app.api.v1.agents_ext import workflow_router
from app.api.v1.agents_ext import task_router
from app.api.v1.agents_ext import browser_router
from app.api.v1.vault import router as vault_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(chat_router)
api_v1_router.include_router(models_router)
api_v1_router.include_router(agents_router)
api_v1_router.include_router(mcp_router)
api_v1_router.include_router(plugins_router)
api_v1_router.include_router(skills_router)
api_v1_router.include_router(automation_router)
api_v1_router.include_router(voice_router)
api_v1_router.include_router(memory_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(marketplace_router)
api_v1_router.include_router(ceo_router)
api_v1_router.include_router(sales_router)
api_v1_router.include_router(custom_router)
api_v1_router.include_router(workflow_router)
api_v1_router.include_router(task_router)
api_v1_router.include_router(browser_router)
api_v1_router.include_router(vault_router)

__all__ = ["api_v1_router"]
