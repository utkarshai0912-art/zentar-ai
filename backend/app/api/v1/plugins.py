"""
Zentar Intelligence — Plugin Manager

Lifecycle management for plugins: install, enable, disable, uninstall,
and configuration management.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.security import get_current_user
from app.plugins.manager import PluginManager

logger = logging.getLogger("zentar.api.plugins")
router = APIRouter(prefix="/plugins", tags=["plugins"])


# ──────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────

class InstallPluginRequest(BaseModel):
    plugin_id: str
    source: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class UpdatePluginConfigRequest(BaseModel):
    config: Dict[str, Any]


class PluginMarketplaceQuery(BaseModel):
    category: Optional[str] = None
    query: Optional[str] = None
    page: int = 1
    page_size: int = 20


# Global reference (populated during app setup)
plugin_manager_ref: Optional[PluginManager] = None


# ──────────────────────────────────────────
# Routes
# ──────────────────────────────────────────

@router.get("")
async def list_plugins(
    enabled_only: bool = Query(False),
    user_id: str = Depends(get_current_user),
):
    """List all plugins."""
    if not plugin_manager_ref:
        return {"success": True, "data": []}
    return {
        "success": True,
        "data": plugin_manager_ref.list_plugins(enabled_only=enabled_only),
    }


@router.get("/marketplace")
async def list_marketplace(
    category: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user),
):
    """Browse the plugin marketplace."""
    from app.plugins.registry import plugin_registry

    plugins = plugin_registry.list_plugins(category=category)

    if query:
        query = query.lower()
        plugins = [p for p in plugins if query in p.name.lower() or query in p.description.lower()]

    total = len(plugins)
    start = (page - 1) * page_size
    items = plugins[start:start + page_size]

    return {
        "success": True,
        "data": {
            "items": [p.to_dict() for p in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


@router.get("/categories")
async def list_categories(
    user_id: str = Depends(get_current_user),
):
    """List plugin categories."""
    from app.plugins.registry import plugin_registry
    return {"success": True, "data": plugin_registry.list_categories()}


@router.get("/{plugin_id}")
async def get_plugin(
    plugin_id: str,
    user_id: str = Depends(get_current_user),
):
    """Get plugin details."""
    from app.plugins.registry import plugin_registry
    plugin = plugin_registry.get(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")

    result = plugin.to_dict()
    if plugin_manager_ref:
        result["config"] = plugin_manager_ref.get_config(plugin_id)
        sandbox = plugin_manager_ref.get_sandbox(plugin_id)
        result["sandbox"] = sandbox.to_dict() if sandbox else None

    return {"success": True, "data": result}


@router.post("/install")
async def install_plugin(
    request: InstallPluginRequest,
    user_id: str = Depends(get_current_user),
):
    """Install a plugin."""
    if not plugin_manager_ref:
        raise HTTPException(status_code=500, detail="Plugin manager not initialized")

    success = await plugin_manager_ref.install(
        plugin_id=request.plugin_id,
        source=request.source,
        config=request.config,
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to install plugin")
    return {"success": True, "message": f"Plugin '{request.plugin_id}' installed"}


@router.post("/{plugin_id}/enable")
async def enable_plugin(
    plugin_id: str,
    request: Optional[UpdatePluginConfigRequest] = None,
    user_id: str = Depends(get_current_user),
):
    """Enable a plugin."""
    if not plugin_manager_ref:
        raise HTTPException(status_code=500, detail="Plugin manager not initialized")

    success = await plugin_manager_ref.enable(plugin_id, request.config if request else None)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to enable plugin")
    return {"success": True, "message": f"Plugin '{plugin_id}' enabled"}


@router.post("/{plugin_id}/disable")
async def disable_plugin(
    plugin_id: str,
    user_id: str = Depends(get_current_user),
):
    """Disable a plugin."""
    if not plugin_manager_ref:
        raise HTTPException(status_code=500, detail="Plugin manager not initialized")

    success = await plugin_manager_ref.disable(plugin_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to disable plugin")
    return {"success": True, "message": f"Plugin '{plugin_id}' disabled"}


@router.delete("/{plugin_id}")
async def uninstall_plugin(
    plugin_id: str,
    user_id: str = Depends(get_current_user),
):
    """Uninstall a plugin."""
    if not plugin_manager_ref:
        raise HTTPException(status_code=500, detail="Plugin manager not initialized")

    success = await plugin_manager_ref.uninstall(plugin_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to uninstall plugin")
    return {"success": True, "message": f"Plugin '{plugin_id}' uninstalled"}


@router.put("/{plugin_id}/config")
async def update_plugin_config(
    plugin_id: str,
    request: UpdatePluginConfigRequest,
    user_id: str = Depends(get_current_user),
):
    """Update plugin configuration."""
    if not plugin_manager_ref:
        raise HTTPException(status_code=500, detail="Plugin manager not initialized")

    success = plugin_manager_ref.update_config(plugin_id, request.config)
    if not success:
        raise HTTPException(status_code=404, detail="Plugin not found or not configured")
    return {"success": True, "message": "Configuration updated"}


@router.get("/stats")
async def plugin_stats(
    user_id: str = Depends(get_current_user),
):
    """Get plugin system statistics."""
    if not plugin_manager_ref:
        return {"success": True, "data": {"total": 0, "installed": 0, "enabled": 0, "sandboxes_active": 0}}
    return {"success": True, "data": plugin_manager_ref.get_stats()}
