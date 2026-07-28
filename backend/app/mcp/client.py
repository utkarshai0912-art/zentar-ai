"""
Zentar Intelligence — MCP Client

Connects to external MCP servers for tool/resource/prompt discovery
and execution. Supports SSE and WebSocket transports.
"""

import asyncio
import json
import logging
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

import aiohttp

from app.core.config import get_settings

logger = logging.getLogger("zentar.mcp.client")

settings = get_settings()


class MCPClient:
    """Client for connecting to external MCP servers.

    Supports connecting via SSE (HTTP) transport and discovering
    tools, resources, and prompts from remote MCP servers.
    """

    def __init__(self, client_id: str, name: str = "MCP Client"):
        self.client_id = client_id
        self.name = name
        self._server_url: Optional[str] = None
        self._auth_token: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._connected = False
        self._capabilities: Dict[str, Any] = {}
        self._tools: List[Dict[str, Any]] = []
        self._resources: List[Dict[str, Any]] = []
        self._prompts: List[Dict[str, Any]] = []

    async def connect(
        self,
        server_url: str,
        auth_token: Optional[str] = None,
        timeout: int = 10,
    ) -> bool:
        """Connect to an MCP server and negotiate capabilities."""
        self._server_url = server_url.rstrip("/")
        self._auth_token = auth_token

        headers = {"Content-Type": "application/json"}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        try:
            self._session = aiohttp.ClientSession(headers=headers)

            # Initialize connection
            async with self._session.post(
                f"{self._server_url}/mcp/initialize",
                json={
                    "protocolVersion": "0.1.0",
                    "clientInfo": {
                        "name": self.name,
                        "version": "0.1.0",
                    },
                },
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status != 200:
                    logger.error("MCP connect failed: %d", resp.status)
                    return False
                result = await resp.json()
                self._capabilities = result.get("capabilities", {})

            # Discover tools, resources, prompts
            await self._discover()
            self._connected = True
            logger.info(
                "Connected to MCP server %s: %d tools, %d resources",
                server_url,
                len(self._tools),
                len(self._resources),
            )
            return True

        except asyncio.TimeoutError:
            logger.error("MCP connect timeout to %s", server_url)
            return False
        except Exception as e:
            logger.error("MCP connect failed to %s: %s", server_url, e)
            return False

    async def _discover(self):
        """Discover tools, resources, and prompts from the server."""
        if not self._session or not self._server_url:
            return

        # List tools
        if "tools" in self._capabilities:
            try:
                async with self._session.post(
                    f"{self._server_url}/mcp/tools/list",
                    json={},
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self._tools = data.get("tools", [])
            except Exception as e:
                logger.warning("Failed to list MCP tools: %s", e)

        # List resources
        if "resources" in self._capabilities:
            try:
                async with self._session.post(
                    f"{self._server_url}/mcp/resources/list",
                    json={},
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self._resources = data.get("resources", [])
            except Exception as e:
                logger.warning("Failed to list MCP resources: %s", e)

        # List prompts
        if "prompts" in self._capabilities:
            try:
                async with self._session.post(
                    f"{self._server_url}/mcp/prompts/list",
                    json={},
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self._prompts = data.get("prompts", [])
            except Exception as e:
                logger.warning("Failed to list MCP prompts: %s", e)

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the remote MCP server."""
        if not self._session or not self._server_url:
            return {"isError": True, "content": [{"type": "text", "text": "Not connected"}]}

        try:
            async with self._session.post(
                f"{self._server_url}/mcp/tools/call",
                json={"name": name, "arguments": arguments},
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    return {"isError": True, "content": [{"type": "text", "text": error_text}]}
                return await resp.json()
        except Exception as e:
            return {"isError": True, "content": [{"type": "text", "text": str(e)}]}

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource from the remote MCP server."""
        if not self._session or not self._server_url:
            return {"isError": True, "contents": []}

        try:
            async with self._session.post(
                f"{self._server_url}/mcp/resources/read",
                json={"uri": uri},
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    return {"isError": True, "contents": []}
                return await resp.json()
        except Exception as e:
            return {"isError": True, "contents": []}

    async def get_prompt(self, name: str, arguments: Optional[Dict] = None) -> Dict[str, Any]:
        """Get a prompt from the remote MCP server."""
        if not self._session or not self._server_url:
            return {"isError": True, "messages": []}

        try:
            async with self._session.post(
                f"{self._server_url}/mcp/prompts/get",
                json={"name": name, "arguments": arguments or {}},
            ) as resp:
                if resp.status != 200:
                    return {"isError": True, "messages": []}
                return await resp.json()
        except Exception as e:
            return {"isError": True, "messages": []}

    async def disconnect(self):
        """Disconnect from the MCP server."""
        self._connected = False
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("Disconnected from MCP server: %s", self._server_url)

    @property
    def is_connected(self) -> bool:
        return self._connected

    def to_dict(self) -> Dict[str, Any]:
        """Serialize client state."""
        return {
            "client_id": self.client_id,
            "name": self.name,
            "server_url": self._server_url,
            "connected": self._connected,
            "tools_count": len(self._tools),
            "resources_count": len(self._resources),
            "prompts_count": len(self._prompts),
        }


class MCPClientManager:
    """Manages multiple MCP client connections."""

    def __init__(self):
        self._clients: Dict[str, MCPClient] = {}

    async def connect(
        self,
        server_url: str,
        name: Optional[str] = None,
        auth_token: Optional[str] = None,
    ) -> Optional[MCPClient]:
        """Create and connect a new MCP client."""
        client_id = str(uuid.uuid4())
        client = MCPClient(client_id, name or f"MCP-{server_url[:30]}")
        success = await client.connect(server_url, auth_token)
        if success:
            self._clients[client_id] = client
            return client
        return None

    def get(self, client_id: str) -> Optional[MCPClient]:
        """Get a client by ID."""
        return self._clients.get(client_id)

    async def disconnect(self, client_id: str):
        """Disconnect and remove a client."""
        client = self._clients.pop(client_id, None)
        if client:
            await client.disconnect()

    async def disconnect_all(self):
        """Disconnect all clients."""
        for client in self._clients.values():
            await client.disconnect()
        self._clients.clear()

    def list_clients(self) -> List[Dict[str, Any]]:
        """List all MCP clients."""
        return [c.to_dict() for c in self._clients.values()]


# Global MCP client manager
mcp_client_manager = MCPClientManager()
