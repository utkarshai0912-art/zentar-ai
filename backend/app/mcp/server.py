"""
Zentar Intelligence — MCP Server Implementation

Model Context Protocol (MCP) server for exposing tools, resources,
and prompts to MCP clients.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from app.core.config import get_settings

logger = logging.getLogger("zentar.mcp.server")

settings = get_settings()


class MCPServer:
    """MCP server for exposing capabilities to MCP clients.

    Implements the Model Context Protocol specification for tool,
    resource, and prompt exposure.
    """

    def __init__(self, server_id: str, name: str = "Zentar MCP Server"):
        self.server_id = server_id
        self.name = name
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._resources: Dict[str, Dict[str, Any]] = {}
        self._prompts: Dict[str, Dict[str, Any]] = {}
        self._version = "0.1.0"
        self._enabled = True

    @property
    def capabilities(self) -> Dict[str, Any]:
        """Get server capabilities for protocol negotiation."""
        return {
            "tools": {
                "list": bool(self._tools),
                "call": bool(self._tools),
            },
            "resources": {
                "list": bool(self._resources),
                "read": bool(self._resources),
                "subscribe": bool(self._resources),
            },
            "prompts": {
                "list": bool(self._prompts),
                "get": bool(self._prompts),
            },
            "logging": {},
        }

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Optional[callable] = None,
    ):
        """Register an MCP tool."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema,
            "handler": handler,
        }
        logger.info("MCP server registered tool: %s", name)

    def register_resource(
        self,
        uri: str,
        name: str,
        description: str,
        mime_type: str = "text/plain",
        handler: Optional[callable] = None,
    ):
        """Register an MCP resource."""
        self._resources[uri] = {
            "uri": uri,
            "name": name,
            "description": description,
            "mimeType": mime_type,
            "handler": handler,
        }
        logger.info("MCP server registered resource: %s (%s)", name, uri)

    def register_prompt(
        self,
        name: str,
        description: str,
        arguments: Optional[List[Dict[str, Any]]] = None,
        handler: Optional[callable] = None,
    ):
        """Register an MCP prompt template."""
        self._prompts[name] = {
            "name": name,
            "description": description,
            "arguments": arguments or [],
            "handler": handler,
        }
        logger.info("MCP server registered prompt: %s", name)

    def unregister_tool(self, name: str):
        """Unregister a tool."""
        self._tools.pop(name, None)

    def get_tools_list(self) -> List[Dict[str, Any]]:
        """Get the list of available tools (without handlers)."""
        return [
            {"name": t["name"], "description": t["description"], "inputSchema": t["inputSchema"]}
            for t in self._tools.values()
        ]

    def get_resources_list(self) -> List[Dict[str, Any]]:
        """Get the list of available resources."""
        return [
            {"uri": r["uri"], "name": r["name"], "description": r["description"], "mimeType": r["mimeType"]}
            for r in self._resources.values()
        ]

    def get_prompts_list(self) -> List[Dict[str, Any]]:
        """Get the list of available prompts."""
        return [
            {"name": p["name"], "description": p["description"], "arguments": p["arguments"]}
            for p in self._prompts.values()
        ]

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a registered tool."""
        tool = self._tools.get(name)
        if not tool:
            return {"isError": True, "content": [{"type": "text", "text": f"Tool '{name}' not found"}]}

        if not tool["handler"]:
            return {"isError": True, "content": [{"type": "text", "text": f"Tool '{name}' has no handler"}]}

        try:
            result = await tool["handler"](**arguments)
            return {
                "content": [{"type": "text", "text": str(result)}],
            }
        except Exception as e:
            logger.error("MCP tool call failed: %s", e, exc_info=True)
            return {"isError": True, "content": [{"type": "text", "text": str(e)}]}

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read an MCP resource."""
        resource = self._resources.get(uri)
        if not resource:
            return {"isError": True, "contents": []}

        if not resource["handler"]:
            return {"isError": True, "contents": []}

        try:
            content = await resource["handler"]()
            return {
                "contents": [{
                    "uri": uri,
                    "mimeType": resource["mimeType"],
                    "text": str(content),
                }],
            }
        except Exception as e:
            return {"isError": True, "contents": []}

    async def get_prompt(self, name: str, arguments: Optional[Dict] = None) -> Dict[str, Any]:
        """Get an MCP prompt with arguments."""
        prompt = self._prompts.get(name)
        if not prompt:
            return {"isError": True, "messages": []}

        if not prompt["handler"]:
            return {"isError": True, "messages": []}

        try:
            messages = await prompt["handler"](**(arguments or {}))
            return {"messages": messages if isinstance(messages, list) else []}
        except Exception as e:
            return {"isError": True, "messages": []}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize server state."""
        return {
            "id": self.server_id,
            "name": self.name,
            "version": self._version,
            "enabled": self._enabled,
            "tools_count": len(self._tools),
            "resources_count": len(self._resources),
            "prompts_count": len(self._prompts),
        }


class MCPServerRegistry:
    """Registry for managing multiple MCP servers."""

    def __init__(self):
        self._servers: Dict[str, MCPServer] = {}

    def register(self, server: MCPServer):
        """Register an MCP server."""
        self._servers[server.server_id] = server
        logger.info("Registered MCP server: %s", server.name)

    def unregister(self, server_id: str):
        """Unregister an MCP server."""
        self._servers.pop(server_id, None)

    def get(self, server_id: str) -> Optional[MCPServer]:
        """Get a server by ID."""
        return self._servers.get(server_id)

    def list_servers(self) -> List[Dict[str, Any]]:
        """List all registered servers."""
        return [s.to_dict() for s in self._servers.values()]

    def get_combined_tools(self) -> List[Dict[str, Any]]:
        """Get tools from all servers."""
        tools = []
        for server in self._servers.values():
            tools.extend(server.get_tools_list())
        return tools

    def get_combined_resources(self) -> List[Dict[str, Any]]:
        """Get resources from all servers."""
        resources = []
        for server in self._servers.values():
            resources.extend(server.get_resources_list())
        return resources


# Global MCP server registry
mcp_server_registry = MCPServerRegistry()


# Default MCP server
default_mcp_server = MCPServer(server_id="default", name="Zentar Default Server")
mcp_server_registry.register(default_mcp_server)
