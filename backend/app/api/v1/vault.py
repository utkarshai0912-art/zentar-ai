"""
Zentar Intelligence — Secrets Vault API Routes

API endpoints for managing user credentials, environment variables,
third-party integrations, and MCP servers.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.vault_service import VaultService

logger = logging.getLogger("zentar.api.vault")
router = APIRouter(prefix="/vault", tags=["Vault"])


# ── Schemas ─────────────────────────────────

class CredentialCreate(BaseModel):
    provider_name: str = Field(..., description="Provider identifier")
    label: str
    api_key: str
    base_url: Optional[str] = None
    org_id: Optional[str] = None
    project_id: Optional[str] = None
    default_model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    timeout: Optional[int] = 30
    is_enabled: bool = True
    is_default: bool = False
    priority: int = 0

class CredentialUpdate(BaseModel):
    label: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    org_id: Optional[str] = None
    project_id: Optional[str] = None
    default_model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    timeout: Optional[int] = None
    is_enabled: Optional[bool] = None
    is_default: Optional[bool] = None
    priority: Optional[int] = None

class EnvVarCreate(BaseModel):
    name: str
    value: str
    category: str = "general"
    is_sensitive: bool = True

class EnvVarUpdate(BaseModel):
    name: Optional[str] = None
    value: Optional[str] = None
    category: Optional[str] = None
    is_sensitive: Optional[bool] = None

class IntegrationCreate(BaseModel):
    integration_type: str
    label: str
    credentials: Optional[Dict[str, Any]] = None
    is_enabled: bool = True

class IntegrationUpdate(BaseModel):
    label: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None

class McpServerCreate(BaseModel):
    name: str
    description: Optional[str] = None
    server_url: str
    auth_type: str = "none"
    auth_config: Optional[Dict[str, Any]] = None
    permissions: Optional[List[str]] = None
    allowed_agents: Optional[List[str]] = None
    is_enabled: bool = True
    auto_reconnect: bool = False

class McpServerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    server_url: Optional[str] = None
    auth_type: Optional[str] = None
    auth_config: Optional[Dict[str, Any]] = None
    permissions: Optional[List[str]] = None
    allowed_agents: Optional[List[str]] = None
    is_enabled: Optional[bool] = None
    auto_reconnect: Optional[bool] = None

class PlatformKeyUpsert(BaseModel):
    provider_name: str
    label: Optional[str] = None
    api_key: str
    base_url: Optional[str] = None
    org_id: Optional[str] = None
    default_model: Optional[str] = None
    is_active: bool = True


# ── Dependencies ────────────────────────────

async def get_vault_service(db: AsyncSession = Depends(get_db)) -> VaultService:
    return VaultService(db)


# ── AI Provider Credentials ─────────────────

@router.get("/credentials")
async def list_credentials(
    provider: Optional[str] = Query(None, alias="provider_name"),
    enabled_only: bool = Query(False),
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """List the authenticated user's AI provider credentials."""
    items = await vault.list_credentials(user_id, provider_name=provider, enabled_only=enabled_only)
    return {"success": True, "data": {"credentials": items, "total": len(items)}}

@router.get("/credentials/{credential_id}")
async def get_credential(
    credential_id: str,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Get a specific credential (key is masked)."""
    item = await vault.get_credential(credential_id, user_id)
    if not item:
        raise HTTPException(status_code=404, detail="Credential not found")
    return {"success": True, "data": item}

@router.post("/credentials")
async def create_credential(
    body: CredentialCreate,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Add a new AI provider credential."""
    result = await vault.create_credential(user_id, body.model_dump())
    return {"success": True, "data": result, "message": "Credential created"}

@router.put("/credentials/{credential_id}")
async def update_credential(
    credential_id: str,
    body: CredentialUpdate,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Update an existing credential."""
    result = await vault.update_credential(
        credential_id, user_id, body.model_dump(exclude_defaults=True, exclude_none=True)
    )
    if not result:
        raise HTTPException(status_code=404, detail="Credential not found")
    return {"success": True, "data": result, "message": "Credential updated"}

@router.delete("/credentials/{credential_id}")
async def delete_credential(
    credential_id: str,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Delete a credential."""
    ok = await vault.delete_credential(credential_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Credential not found")
    return {"success": True, "message": "Credential deleted"}

@router.post("/credentials/{credential_id}/test")
async def test_credential(
    credential_id: str,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Test a credential by making an API call to the provider."""
    ok, message = await vault.test_credential(credential_id, user_id)
    if not ok:
        return {"success": False, "message": message}
    return {"success": True, "message": message}

@router.post("/credentials/{credential_id}/reveal")
async def reveal_credential(
    credential_id: str,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Reveal the full API key (audited)."""
    key = await vault.reveal_credential_key(credential_id, user_id)
    if not key:
        raise HTTPException(status_code=404, detail="Credential not found")
    return {"success": True, "data": {"api_key": key}}

@router.get("/credentials/providers/list")
async def list_providers():
    """List all supported AI providers."""
    return {
        "success": True,
        "data": {
            "providers": VaultService.PROVIDER_NAMES,
        },
    }


# ── Environment Variables ───────────────────

@router.get("/env-vars")
async def list_env_vars(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """List environment variables."""
    items = await vault.list_env_vars(user_id, category=category, search=search)
    return {"success": True, "data": {"variables": items, "total": len(items)}}

@router.get("/env-vars/categories")
async def get_env_var_categories(
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Get environment variable categories with counts."""
    cats = await vault.get_env_categories(user_id)
    return {"success": True, "data": {"categories": cats}}

@router.get("/env-vars/{var_id}")
async def get_env_var(
    var_id: str,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Get a specific environment variable."""
    item = await vault.get_env_var(var_id, user_id)
    if not item:
        raise HTTPException(status_code=404, detail="Variable not found")
    return {"success": True, "data": item}

@router.post("/env-vars")
async def create_env_var(
    body: EnvVarCreate,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Create an environment variable."""
    result = await vault.create_env_var(user_id, body.model_dump())
    return {"success": True, "data": result, "message": "Variable created"}

@router.put("/env-vars/{var_id}")
async def update_env_var(
    var_id: str,
    body: EnvVarUpdate,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Update an environment variable."""
    result = await vault.update_env_var(
        var_id, user_id, body.model_dump(exclude_defaults=True, exclude_none=True)
    )
    if not result:
        raise HTTPException(status_code=404, detail="Variable not found")
    return {"success": True, "data": result, "message": "Variable updated"}

@router.delete("/env-vars/{var_id}")
async def delete_env_var(
    var_id: str,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Delete an environment variable."""
    ok = await vault.delete_env_var(var_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Variable not found")
    return {"success": True, "message": "Variable deleted"}

@router.post("/env-vars/{var_id}/reveal")
async def reveal_env_var(
    var_id: str,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Reveal a sensitive environment variable value (audited)."""
    value = await vault.reveal_env_var(var_id, user_id)
    if not value:
        raise HTTPException(status_code=404, detail="Variable not found")
    return {"success": True, "data": {"value": value}}


# ── Integrations ────────────────────────────

@router.get("/integrations")
async def list_integrations(
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """List third-party integrations."""
    items = await vault.list_integrations(user_id)
    return {"success": True, "data": {"integrations": items, "total": len(items)}}

@router.get("/integrations/types")
async def list_integration_types():
    """List all supported integration types."""
    return {
        "success": True,
        "data": {"types": VaultService.INTEGRATION_TYPES},
    }

@router.get("/integrations/{integration_id}")
async def get_integration(
    integration_id: str,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Get a specific integration."""
    item = await vault.get_integration(integration_id, user_id)
    if not item:
        raise HTTPException(status_code=404, detail="Integration not found")
    return {"success": True, "data": item}

@router.post("/integrations")
async def create_integration(
    body: IntegrationCreate,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Connect a new integration."""
    result = await vault.create_integration(user_id, body.model_dump())
    return {"success": True, "data": result, "message": "Integration created"}

@router.put("/integrations/{integration_id}")
async def update_integration(
    integration_id: str,
    body: IntegrationUpdate,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Update an integration."""
    result = await vault.update_integration(
        integration_id, user_id, body.model_dump(exclude_defaults=True, exclude_none=True)
    )
    if not result:
        raise HTTPException(status_code=404, detail="Integration not found")
    return {"success": True, "data": result, "message": "Integration updated"}

@router.delete("/integrations/{integration_id}")
async def delete_integration(
    integration_id: str,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Disconnect an integration."""
    ok = await vault.delete_integration(integration_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Integration not found")
    return {"success": True, "message": "Integration deleted"}

@router.post("/integrations/{integration_id}/test")
async def test_integration(
    integration_id: str,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Test an integration connection."""
    ok, message = await vault.test_integration(integration_id, user_id)
    return {"success": ok, "message": message}

@router.put("/integrations/{integration_id}/toggle")
async def toggle_integration(
    integration_id: str,
    enabled: bool = Query(...),
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Enable or disable an integration."""
    result = await vault.update_integration(
        integration_id, user_id, {"is_enabled": enabled}
    )
    if not result:
        raise HTTPException(status_code=404, detail="Integration not found")
    return {"success": True, "data": result, "message": f"Integration {'enabled' if enabled else 'disabled'}"}


# ── MCP Servers ─────────────────────────────

@router.get("/mcp-servers")
async def list_mcp_servers(
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """List user-registered MCP servers."""
    items = await vault.list_mcp_servers(user_id)
    return {"success": True, "data": {"servers": items, "total": len(items)}}

@router.get("/mcp-servers/{server_id}")
async def get_mcp_server(
    server_id: str,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Get a specific MCP server."""
    item = await vault.get_mcp_server(server_id, user_id)
    if not item:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return {"success": True, "data": item}

@router.post("/mcp-servers")
async def create_mcp_server(
    body: McpServerCreate,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Register a new MCP server."""
    result = await vault.create_mcp_server(user_id, body.model_dump())
    return {"success": True, "data": result, "message": "MCP server created"}

@router.put("/mcp-servers/{server_id}")
async def update_mcp_server(
    server_id: str,
    body: McpServerUpdate,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Update an MCP server."""
    result = await vault.update_mcp_server(
        server_id, user_id, body.model_dump(exclude_defaults=True, exclude_none=True)
    )
    if not result:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return {"success": True, "data": result, "message": "MCP server updated"}

@router.delete("/mcp-servers/{server_id}")
async def delete_mcp_server(
    server_id: str,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Delete an MCP server."""
    ok = await vault.delete_mcp_server(server_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return {"success": True, "message": "MCP server deleted"}

@router.post("/mcp-servers/{server_id}/test")
async def test_mcp_server(
    server_id: str,
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Test an MCP server connection."""
    ok, message = await vault.test_mcp_server(server_id, user_id)
    return {"success": ok, "message": message}

@router.put("/mcp-servers/{server_id}/toggle")
async def toggle_mcp_server(
    server_id: str,
    enabled: bool = Query(...),
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Enable or disable an MCP server."""
    result = await vault.update_mcp_server(
        server_id, user_id, {"is_enabled": enabled}
    )
    if not result:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return {"success": True, "data": result, "message": f"MCP server {'enabled' if enabled else 'disabled'}"}


# ── Configuration Export ────────────────────

@router.get("/config")
async def get_user_ai_config(
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Get the user's resolved AI provider configuration (for agent use)."""
    config = await vault.get_user_provider_config(user_id)
    return {
        "success": True,
        "data": {
            "configured_providers": list(config.keys()),
            "provider_count": len(config),
        },
    }


# ── Audit Log (Admin) ───────────────────────

@router.get("/audit-logs")
async def list_audit_logs(
    user_id: str = Depends(get_current_user),
    vault: VaultService = Depends(get_vault_service),
):
    """Get audit logs for the current user's actions."""
    from sqlalchemy.future import select
    from app.models.vault import AuditLog

    db = vault.db
    q = select(AuditLog).where(
        AuditLog.user_id == user_id
    ).order_by(AuditLog.created_at.desc()).limit(100)
    result = await db.execute(q)
    logs = []
    for entry in result.scalars().all():
        logs.append({
            "id": entry.id,
            "action": entry.action,
            "resource_type": entry.resource_type,
            "resource_id": entry.resource_id,
            "details": entry.details,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        })
    return {"success": True, "data": {"logs": logs, "total": len(logs)}}