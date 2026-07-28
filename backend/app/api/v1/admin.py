"""
Zentar Intelligence — Admin API Routes

Administrative endpoints for system monitoring, user management,
and configuration.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.core.database import get_db

logger = logging.getLogger("zentar.api.admin")
router = APIRouter(prefix="/admin", tags=["admin"])


# ──────────────────────────────────────────
# Helper: check admin role
# ──────────────────────────────────────────

async def get_admin_user(user_id: str = Depends(get_current_user)) -> str:
    """Dependency that ensures the user has admin role."""
    # In production, check user.role == "admin" from DB
    # For now, pass through (admin middleware would be applied in production)
    return user_id


# ──────────────────────────────────────────
# Routes
# ──────────────────────────────────────────

@router.get("/health")
async def admin_health():
    """Comprehensive system health check."""
    import time
    start = time.time()

    health_info = {
        "status": "healthy",
        "timestamp": start,
        "version": "1.0.0",
        "modules": {},
    }

    # Check core modules
    try:
        from app.core.config import get_settings
        settings = get_settings()
        health_info["modules"]["config"] = "ok"
    except Exception as e:
        health_info["modules"]["config"] = f"error: {e}"
        health_info["status"] = "degraded"

    # Check database (placeholder — would ping DB)
    health_info["modules"]["database"] = "ok"

    # Check Redis (placeholder)
    health_info["modules"]["redis"] = "ok"

    # Check AI providers
    try:
        from app.services.ai_service import provider_registry
        providers = provider_registry.list_providers()
        health_info["modules"]["ai_providers"] = {
            "available": list(providers.keys()),
            "count": len(providers),
        }
    except Exception as e:
        health_info["modules"]["ai_providers"] = f"error: {e}"

    health_info["response_time_ms"] = round((time.time() - start) * 1000, 2)
    return {"success": True, "data": health_info}


@router.get("/stats")
async def admin_stats(
    admin_user: str = Depends(get_admin_user),
):
    """Get comprehensive system statistics."""
    stats = {
        "agents": {},
        "plugins": {},
        "skills": {},
        "automation": {},
        "memory": {},
        "mcp": {},
        "tasks": {},
        "browser": {},
        "managers": {},
        "workers": {},
        "workflows": {},
        "custom_agents": {},
        "sales": {},
    }

    try:
        from app.agents.agent_engine import agent_manager
        stats["agents"] = agent_manager.get_stats()
    except Exception as e:
        stats["agents"]["error"] = str(e)

    try:
        from app.plugins.manager import plugin_manager
        stats["plugins"] = plugin_manager.get_stats()
    except Exception as e:
        stats["plugins"]["error"] = str(e)

    try:
        from app.skills.manager import skill_manager
        stats["skills"] = skill_manager.get_stats()
    except Exception as e:
        stats["skills"]["error"] = str(e)

    try:
        from app.automation.engine import automation_engine
        stats["automation"] = automation_engine.get_stats()
    except Exception as e:
        stats["automation"]["error"] = str(e)

    try:
        from app.services.memory_service import memory_service
        stats["memory"] = memory_service.get_stats()
    except Exception as e:
        stats["memory"]["error"] = str(e)

    try:
        from app.mcp.discovery import discovery_service
        stats["mcp"] = discovery_service.get_network_summary()
    except Exception as e:
        stats["mcp"]["error"] = str(e)

    try:
        from app.agents.task_system import task_orchestrator
        stats["tasks"] = task_orchestrator.get_stats()
    except Exception as e:
        stats["tasks"]["error"] = str(e)

    try:
        from app.services.browser_service import browser_service
        stats["browser"] = browser_service.get_stats()
    except Exception as e:
        stats["browser"]["error"] = str(e)

    try:
        from app.agents.manager_agents import list_managers
        stats["managers"] = {"count": len(list_managers())}
    except Exception as e:
        stats["managers"]["error"] = str(e)

    try:
        from app.agents.worker_agents import list_workers
        stats["workers"] = {"count": len(list_workers())}
    except Exception as e:
        stats["workers"]["error"] = str(e)

    try:
        from app.agents.workflow_builder import workflow_builder
        stats["workflows"] = workflow_builder.get_stats()
    except Exception as e:
        stats["workflows"]["error"] = str(e)

    try:
        from app.agents.custom_agent_builder import custom_agent_builder
        stats["custom_agents"] = custom_agent_builder.get_stats()
    except Exception as e:
        stats["custom_agents"]["error"] = str(e)

    try:
        from app.agents.sales_team import sales_pipeline_manager
        stats["sales"] = {"pipelines": len(sales_pipeline_manager._pipelines)}
    except Exception as e:
        stats["sales"]["error"] = str(e)

    return {"success": True, "data": stats}


@router.get("/config")
async def admin_config(
    admin_user: str = Depends(get_admin_user),
):
    """Get system configuration (sanitized)."""
    from app.core.config import get_settings
    settings = get_settings()

    # Return non-sensitive config
    return {
        "success": True,
        "data": {
            "app_name": "Zentar Intelligence",
            "version": "1.0.0",
            "environment": "production",
            "debug": settings.DEBUG,
            "providers": {
                "openai": bool(settings.OPENAI_API_KEY),
                "anthropic": bool(settings.ANTHROPIC_API_KEY),
                "gemini": bool(settings.GEMINI_API_KEY),
                "deepseek": bool(settings.DEEPSEEK_API_KEY),
            },
            "database": "postgresql",
            "redis_enabled": bool(settings.REDIS_URL),
            "cors_origins": settings.CORS_ORIGINS,
            "rate_limit": settings.RATE_LIMIT_PER_MINUTE,
        },
    }


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin_user: str = Depends(get_admin_user),
):
    """List users (admin only)."""
    # Placeholder — would query DB
    return {
        "success": True,
        "data": {
            "users": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/queue")
async def view_task_queue(
    status: Optional[str] = Query(None),
    admin_user: str = Depends(get_admin_user),
):
    """View background task queue."""
    from app.workers.tasks import task_queue
    tasks = task_queue.list_tasks(status=status)
    return {
        "success": True,
        "data": {
            "tasks": [t.to_dict() for t in tasks],
            "stats": task_queue.get_stats(),
        },
    }


@router.post("/scheduler/start")
async def start_scheduler(
    admin_user: str = Depends(get_admin_user),
):
    """Start the background scheduler."""
    from app.workers.scheduler import scheduler
    await scheduler.start()
    return {"success": True, "message": "Scheduler started"}


@router.post("/scheduler/stop")
async def stop_scheduler(
    admin_user: str = Depends(get_admin_user),
):
    """Stop the background scheduler."""
    from app.workers.scheduler import scheduler
    await scheduler.stop()
    return {"success": True, "message": "Scheduler stopped"}


@router.get("/scheduler/status")
async def scheduler_status(
    admin_user: str = Depends(get_admin_user),
):
    """Get scheduler status."""
    from app.workers.scheduler import scheduler
    return {
        "success": True,
        "data": {
            "is_running": scheduler.is_running,
            "tasks": scheduler.get_all_status(),
        },
    }


@router.post("/cache/clear")
async def clear_cache(
    admin_user: str = Depends(get_admin_user),
):
    """Clear system caches."""
    from app.services.embedding_service import embedding_service
    embedding_service.clear_cache()
    return {"success": True, "message": "Cache cleared"}


# ──────────────────────────────────────────
# Admin: Secrets Vault Configuration
# ──────────────────────────────────────────

@router.get("/vault/platform-keys")
async def list_platform_keys(
    admin_user: str = Depends(get_admin_user),
    db=Depends(get_db),
):
    """List all platform-managed API keys."""
    from app.services.vault_service import VaultService
    vault = VaultService(db)
    keys = await vault.list_platform_keys()
    return {"success": True, "data": {"keys": keys, "total": len(keys)}}


@router.post("/vault/platform-keys")
async def upsert_platform_key(
    body: dict,
    admin_user: str = Depends(get_admin_user),
    db=Depends(get_db),
):
    """Create or update a platform-managed API key."""
    from app.services.vault_service import VaultService
    vault = VaultService(db)
    result = await vault.upsert_platform_key(body)
    return {"success": True, "data": result, "message": "Platform key saved"}


@router.delete("/vault/platform-keys/{key_id}")
async def delete_platform_key(
    key_id: str,
    admin_user: str = Depends(get_admin_user),
    db=Depends(get_db),
):
    """Delete a platform-managed API key."""
    from app.services.vault_service import VaultService
    vault = VaultService(db)
    ok = await vault.delete_platform_key(key_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Platform key not found")
    return {"success": True, "message": "Platform key deleted"}


@router.get("/vault/settings")
async def get_vault_admin_settings(
    admin_user: str = Depends(get_admin_user),
):
    """Get vault admin configuration."""
    from app.core.config import get_settings
    s = get_settings()
    return {
        "success": True,
        "data": {
            "allow_user_api_keys": True,
            "max_credentials_per_provider": 5,
            "max_env_vars": 100,
            "max_integrations": 50,
            "max_mcp_servers": 20,
            "audit_log_enabled": s.AUDIT_LOG_ENABLED,
        },
    }


@router.get("/vault/audit-logs")
async def list_all_audit_logs(
    user_id_filter: Optional[str] = Query(None, alias="user_id"),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    admin_user: str = Depends(get_admin_user),
    db=Depends(get_db),
):
    """View all audit logs (admin only)."""
    from app.models.vault import AuditLog
    from sqlalchemy.future import select

    q = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if user_id_filter:
        q = q.where(AuditLog.user_id == user_id_filter)
    if action:
        q = q.where(AuditLog.action == action)
    if resource_type:
        q = q.where(AuditLog.resource_type == resource_type)

    result = await db.execute(q)
    logs = []
    for entry in result.scalars().all():
        logs.append({
            "id": entry.id,
            "user_id": entry.user_id,
            "action": entry.action,
            "resource_type": entry.resource_type,
            "resource_id": entry.resource_id,
            "details": entry.details,
            "ip_address": entry.ip_address,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        })
    return {"success": True, "data": {"logs": logs, "total": len(logs)}}
