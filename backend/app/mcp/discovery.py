"""
Zentar Intelligence — MCP Discovery

Service for discovering MCP tools, resources, and prompts
across both local and remote MCP servers.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from app.mcp.client import mcp_client_manager
from app.mcp.server import default_mcp_server, mcp_server_registry

logger = logging.getLogger("zentar.mcp.discovery")


class MCPDiscoveryService:
    """Discovers and aggregates MCP capabilities across servers."""

    def __init__(self):
        self._tool_cache: Dict[str, List[Dict]] = {}
        self._resource_cache: Dict[str, List[Dict]] = {}

    async def discover_all_tools(self) -> List[Dict[str, Any]]:
        """Discover tools from all connected servers + local server."""
        tools = []

        # Local server tools
        tools.extend(default_mcp_server.get_tools_list())

        # Other registered servers
        for server in mcp_server_registry.list_servers():
            srv = mcp_server_registry.get(server["id"])
            if srv:
                tools.extend(srv.get_tools_list())

        # Remote clients
        for client in mcp_client_manager.list_clients():
            cl = mcp_client_manager.get(client["client_id"])
            if cl and hasattr(cl, "_tools"):
                tools.extend(cl._tools)

        return tools

    async def discover_all_resources(self) -> List[Dict[str, Any]]:
        """Discover resources from all servers."""
        resources = []
        resources.extend(default_mcp_server.get_resources_list())

        for server in mcp_server_registry.list_servers():
            srv = mcp_server_registry.get(server["id"])
            if srv:
                resources.extend(srv.get_resources_list())

        return resources

    async def discover_all_prompts(self) -> List[Dict[str, Any]]:
        """Discover prompts from all servers."""
        prompts = []
        prompts.extend(default_mcp_server.get_prompts_list())

        for server in mcp_server_registry.list_servers():
            srv = mcp_server_registry.get(server["id"])
            if srv:
                prompts.extend(srv.get_prompts_list())

        return prompts

    async def call_tool(self, server_id: str, name: str, arguments: Dict) -> Dict:
        """Call a tool on a specific server or find it across all servers."""
        # Try local server
        if server_id == "default" or not server_id:
            return await default_mcp_server.call_tool(name, arguments)

        # Try other registered servers
        server = mcp_server_registry.get(server_id)
        if server:
            return await server.call_tool(name, arguments)

        # Try remote clients
        client = mcp_client_manager.get(server_id)
        if client:
            return await client.call_tool(name, arguments)

        # Search all servers
        srv = mcp_server_registry.get(server_id)
        if srv:
            return await srv.call_tool(name, arguments)

        # Search clients by server_url prefix
        for cl in mcp_client_manager.list_clients():
            cl_obj = mcp_client_manager.get(cl["client_id"])
            if cl_obj and hasattr(cl_obj, "_tools"):
                for tool in cl_obj._tools:
                    if tool.get("name") == name:
                        return await cl_obj.call_tool(name, arguments)

        return {"isError": True, "content": [{"type": "text", "text": f"Server '{server_id}' not found"}]}

    def get_server_info(self, server_id: str) -> Optional[Dict]:
        """Get server info by ID."""
        if server_id == "default":
            return default_mcp_server.to_dict()

        server = mcp_server_registry.get(server_id)
        if server:
            return server.to_dict()

        client = mcp_client_manager.get(server_id)
        if client:
            return client.to_dict()

        return None

    def get_network_summary(self) -> Dict[str, Any]:
        """Get a summary of the entire MCP network."""
        local_servers = mcp_server_registry.list_servers()
        remote_clients = mcp_client_manager.list_clients()

        total_tools = sum(
            s.get("tools_count", 0) for s in local_servers
        ) + sum(
            c.get("tools_count", 0) for c in remote_clients
        )

        return {
            "local_servers": len(local_servers),
            "remote_connections": len(remote_clients),
            "total_tools": total_tools,
            "servers": local_servers,
            "clients": remote_clients,
        }


# Global discovery service
discovery_service = MCPDiscoveryService()
