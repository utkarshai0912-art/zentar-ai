"""
Zentar Intelligence — Coding Agent

Specialized agent for coding tasks with workspace management,
file operations, and code execution capabilities.
"""

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.agents.agent_engine import AgentConfig, AgentEngine, agent_manager
from app.agents.tool_registry import Tool, tool_registry
from app.core.config import get_settings

logger = logging.getLogger("zentar.agents.coding")

settings = get_settings()


class Workspace:
    """Isolated workspace for coding agent file operations."""

    def __init__(self, workspace_id: str, base_path: Optional[str] = None):
        self.workspace_id = workspace_id
        self.base_path = Path(base_path or tempfile.mkdtemp(prefix="zentar_ws_"))
        self.base_path.mkdir(parents=True, exist_ok=True)

    @property
    def path(self) -> str:
        return str(self.base_path)

    def resolve(self, path: str) -> Path:
        """Resolve a path within the workspace, preventing escapes."""
        full = (self.base_path / path).resolve()
        if not str(full).startswith(str(self.base_path.resolve())):
            raise PermissionError(f"Path {path} escapes workspace boundary")
        return full

    async def read_file(self, path: str) -> str:
        """Read a file from the workspace."""
        full_path = self.resolve(path)
        if not full_path.exists():
            return f"Error: File {path} not found"
        return full_path.read_text(encoding="utf-8")

    async def write_file(self, path: str, content: str) -> str:
        """Write a file in the workspace."""
        full_path = self.resolve(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        return f"File {path} written ({len(content)} bytes)"

    async def delete_file(self, path: str) -> str:
        """Delete a file from the workspace."""
        full_path = self.resolve(path)
        if full_path.is_file():
            full_path.unlink()
            return f"File {path} deleted"
        return f"Error: {path} is not a file"

    async def list_files(self, path: str = "") -> str:
        """List files in a workspace directory."""
        full_path = self.resolve(path)
        if not full_path.is_dir():
            return f"Error: {path} is not a directory"

        items = []
        for p in sorted(full_path.iterdir()):
            suffix = "/" if p.is_dir() else ""
            items.append(f"{p.name}{suffix}")
        return "\n".join(items) if items else "(empty directory)"

    async def run_command(self, command: str, timeout: int = 30) -> str:
        """Run a shell command in the workspace."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.base_path,
            )
            output = []
            if result.stdout:
                output.append(result.stdout)
            if result.stderr:
                output.append(f"STDERR:\n{result.stderr}")
            if result.returncode != 0:
                output.insert(0, f"Exit code: {result.returncode}")
            return "\n".join(output) if output else "(no output)"
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout}s"
        except Exception as e:
            return f"Error: {str(e)}"

    def cleanup(self):
        """Remove the workspace directory."""
        import shutil
        shutil.rmtree(self.base_path, ignore_errors=True)


class CodingAgent:
    """Specialized coding agent with workspace management."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.workspace = Workspace(agent_id)
        self._engine: Optional[AgentEngine] = None

    async def initialize(self):
        """Initialize the coding agent with tools and engine."""
        # Register coding tools
        coding_tools = [
            Tool(
                name="read_file",
                description="Read a file from the workspace",
                handler=self.workspace.read_file,
                parameters={
                    "path": {
                        "type": "string",
                        "description": "Path to the file (relative to workspace)",
                    }
                },
                required=["path"],
                category="coding",
            ),
            Tool(
                name="write_file",
                description="Write content to a file in the workspace",
                handler=self.workspace.write_file,
                parameters={
                    "path": {
                        "type": "string",
                        "description": "Path to the file (relative to workspace)",
                    },
                    "content": {
                        "type": "string",
                        "description": "File content to write",
                    },
                },
                required=["path", "content"],
                category="coding",
            ),
            Tool(
                name="list_files",
                description="List files in a workspace directory",
                handler=self.workspace.list_files,
                parameters={
                    "path": {
                        "type": "string",
                        "description": "Directory path (relative to workspace, default: root)",
                    }
                },
                category="coding",
            ),
            Tool(
                name="run_command",
                description="Run a shell command in the workspace",
                handler=self.workspace.run_command,
                parameters={
                    "command": {
                        "type": "string",
                        "description": "Command to run",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 30)",
                    },
                },
                required=["command"],
                category="coding",
            ),
            Tool(
                name="delete_file",
                description="Delete a file from the workspace",
                handler=self.workspace.delete_file,
                parameters={
                    "path": {
                        "type": "string",
                        "description": "Path to the file (relative to workspace)",
                    }
                },
                required=["path"],
                category="coding",
            ),
        ]

        for tool in coding_tools:
            tool_registry.register(tool)

        # Create agent engine
        self._engine = agent_manager.create_agent(
            name="Coding Agent",
            system_prompt=(
                "You are an expert coding agent. You have a workspace where you can "
                "create, read, edit, and manage files. You can also run commands.\n\n"
                "Guidelines:\n"
                "- Write clean, well-documented code\n"
                "- Use proper error handling\n"
                "- Run tests to verify your work\n"
                "- Ask for clarification when requirements are ambiguous\n"
                "- Commit working code, not broken code\n"
            ),
            tool_categories=["general", "coding"],
            enable_tools=True,
            memory_enabled=True,
        )

    async def execute(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        stream: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute a coding task."""
        if not self._engine:
            await self.initialize()

        async for event in self._engine.execute(message, conversation_id, stream):
            yield event

    def cleanup(self):
        """Clean up workspace and resources."""
        self.workspace.cleanup()
        if self._engine:
            agent_manager.delete_agent(self.agent_id)


class CodingAgentManager:
    """Manages coding agent instances."""

    def __init__(self):
        self._agents: Dict[str, CodingAgent] = {}

    async def get_or_create(self, agent_id: str) -> CodingAgent:
        """Get or create a coding agent."""
        if agent_id not in self._agents:
            agent = CodingAgent(agent_id)
            await agent.initialize()
            self._agents[agent_id] = agent
        return self._agents[agent_id]

    def get(self, agent_id: str) -> Optional[CodingAgent]:
        """Get a coding agent by ID."""
        return self._agents.get(agent_id)

    def delete(self, agent_id: str):
        """Delete a coding agent."""
        if agent_id in self._agents:
            self._agents[agent_id].cleanup()
            del self._agents[agent_id]

    def list_workspaces(self) -> List[Dict[str, Any]]:
        """List all active coding workspaces."""
        return [
            {
                "agent_id": aid,
                "workspace_path": agent.workspace.path,
            }
            for aid, agent in self._agents.items()
        ]


# Global coding agent manager
coding_agent_manager = CodingAgentManager()
