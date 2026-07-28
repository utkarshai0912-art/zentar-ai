"""
Zentar Intelligence — MCP API Routes

Endpoints for managing MCP servers and client connections.
"""

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.mcp.auth import mcp_auth_provider
from app.mcp.client import mcp_client_manager
from app.mcp.discovery import discovery_service
from app.mcp.server import MCPServer, default_mcp_server, mcp_server_registry

logger = logging.getLogger("zentar.api.mcp")
router = APIRouter(prefix="/mcp", tags=["mcp"])


# ──────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────

class RegisterToolRequest(BaseModel):
    name: str
    description: str
    input_schema: dict
    server_id: str = "default"


class RegisterResourceRequest(BaseModel):
    uri: str
    name: str
    description: str
    mime_type: str = "text/plain"
    server_id: str = "default"


class RegisterPromptRequest(BaseModel):
    name: str
    description: str
    arguments: Optional[List[dict]] = None
    server_id: str = "default"


class ConnectServerRequest(BaseModel):
    server_url: str
    name: Optional[str] = None
    auth_token: Optional[str] = None


class CallToolRequest(BaseModel):
    server_id: str = "default"
    name: str
    arguments: dict = {}


class RegisterOAuthClientRequest(BaseModel):
    client_name: str
    client_uri: str
    redirect_uris: List[str]
    scopes: Optional[List[str]] = None
    generate_secret: bool = False


# ──────────────────────────────────────────
# Routes
# ──────────────────────────────────────────

@router.get("/tools")
async def list_tools(
    server_id: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user),
):
    """Discover available MCP tools across all servers."""
    tools = await discovery_service.discover_all_tools()
    return {"success": True, "data": {"tools": tools, "total": len(tools)}}


@router.get("/resources")
async def list_resources(
    user_id: str = Depends(get_current_user),
):
    """Discover available MCP resources."""
    resources = await discovery_service.discover_all_resources()
    return {"success": True, "data": {"resources": resources, "total": len(resources)}}


@router.get("/prompts")
async def list_prompts(
    user_id: str = Depends(get_current_user),
):
    """Discover available MCP prompts."""
    prompts = await discovery_service.discover_all_prompts()
    return {"success": True, "data": {"prompts": prompts, "total": len(prompts)}}


@router.post("/tools/register")
async def register_tool(
    request: RegisterToolRequest,
    user_id: str = Depends(get_current_user),
):
    """Register a new MCP tool on a local server."""
    server = mcp_server_registry.get(request.server_id) if request.server_id != "default" else default_mcp_server
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    server.register_tool(
        name=request.name,
        description=request.description,
        input_schema=request.input_schema,
    )
    return {"success": True, "message": f"Tool '{request.name}' registered"}


@router.post("/resources/register")
async def register_resource(
    request: RegisterResourceRequest,
    user_id: str = Depends(get_current_user),
):
    """Register a new MCP resource."""
    server = mcp_server_registry.get(request.server_id) if request.server_id != "default" else default_mcp_server
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    server.register_resource(
        uri=request.uri,
        name=request.name,
        description=request.description,
        mime_type=request.mime_type,
    )
    return {"success": True, "message": f"Resource '{request.name}' registered"}


@router.post("/prompts/register")
async def register_prompt(
    request: RegisterPromptRequest,
    user_id: str = Depends(get_current_user),
):
    """Register a new MCP prompt."""
    server = mcp_server_registry.get(request.server_id) if request.server_id != "default" else default_mcp_server
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    server.register_prompt(
        name=request.name,
        description=request.description,
        arguments=request.arguments,
    )
    return {"success": True, "message": f"Prompt '{request.name}' registered"}


@router.post("/tools/call")
async def call_tool(
    request: CallToolRequest,
    user_id: str = Depends(get_current_user),
):
    """Call a tool on an MCP server."""
    result = await discovery_service.call_tool(
        server_id=request.server_id,
        name=request.name,
        arguments=request.arguments,
    )
    return {"success": not result.get("isError", False), "data": result}


@router.post("/connect")
async def connect_server(
    request: ConnectServerRequest,
    user_id: str = Depends(get_current_user),
):
    """Connect to a remote MCP server."""
    client = await mcp_client_manager.connect(
        server_url=request.server_url,
        name=request.name,
        auth_token=request.auth_token,
    )
    if not client:
        raise HTTPException(status_code=400, detail="Failed to connect to MCP server")
    return {
        "success": True,
        "data": client.to_dict(),
    }


@router.post("/disconnect/{client_id}")
async def disconnect_server(
    client_id: str,
    user_id: str = Depends(get_current_user),
):
    """Disconnect from a remote MCP server."""
    await mcp_client_manager.disconnect(client_id)
    return {"success": True, "message": "Disconnected"}


@router.get("/servers")
async def list_servers(
    user_id: str = Depends(get_current_user),
):
    """List all MCP servers and connections."""
    summary = discovery_service.get_network_summary()
    return {"success": True, "data": summary}


@router.get("/servers/{server_id}")
async def get_server(
    server_id: str,
    user_id: str = Depends(get_current_user),
):
    """Get MCP server details."""
    info = discovery_service.get_server_info(server_id)
    if not info:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"success": True, "data": info}


@router.post("/oauth/register")
async def register_oauth_client(
    request: RegisterOAuthClientRequest,
    user_id: str = Depends(get_current_user),
):
    """Register an OAuth client for MCP."""
    client = mcp_auth_provider.register_client(
        client_name=request.client_name,
        client_uri=request.client_uri,
        redirect_uris=request.redirect_uris,
        scopes=request.scopes,
        generate_secret=request.generate_secret,
    )
    return {"success": True, "data": client}


@router.get("/network")
async def mcp_network_summary(
    user_id: str = Depends(get_current_user),
):
    """Get MCP network summary."""
    return {
        "success": True,
        "data": discovery_service.get_network_summary(),
    }
