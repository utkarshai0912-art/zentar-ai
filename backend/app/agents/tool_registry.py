"""
Zentar Intelligence — Tool Registry

JSON Schema-based tool registry for AI function calling.
Tools are registered with their schemas and handler functions.
"""

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger("zentar.agents.tools")


class Tool:
    """A registered tool with schema and handler."""

    def __init__(
        self,
        name: str,
        description: str,
        handler: Callable[..., Awaitable[str]],
        parameters: Dict[str, Any],
        required: Optional[List[str]] = None,
        category: str = "general",
    ):
        self.name = name
        self.description = description
        self.handler = handler
        self.parameters = parameters
        self.required = required or []
        self.category = category

    def to_openai_schema(self) -> Dict[str, Any]:
        """Return tool definition in OpenAI function-calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required,
                },
            },
        }

    def to_anthropic_schema(self) -> Dict[str, Any]:
        """Return tool definition in Anthropic tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": self.required,
            },
        }

    async def execute(self, **kwargs) -> str:
        """Execute the tool handler with given arguments."""
        try:
            logger.info("Executing tool: %s with args: %s", self.name, kwargs)
            result = await self.handler(**kwargs)
            return result
        except Exception as e:
            logger.error("Tool %s failed: %s", self.name, e, exc_info=True)
            return f"Error executing tool '{self.name}': {str(e)}"


class ToolRegistry:
    """Central registry for all available tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._categories: Dict[str, List[str]] = {}

    def register(self, tool: Tool):
        """Register a tool."""
        self._tools[tool.name] = tool
        if tool.category not in self._categories:
            self._categories[tool.category] = []
        self._categories[tool.category].append(tool.name)
        logger.info("Registered tool: %s (category: %s)", tool.name, tool.category)

    def register_many(self, tools: List[Tool]):
        """Register multiple tools at once."""
        for tool in tools:
            self.register(tool)

    def unregister(self, name: str):
        """Unregister a tool."""
        if name in self._tools:
            category = self._tools[name].category
            self._categories.get(category, []).remove(name)
            del self._tools[name]
            logger.info("Unregistered tool: %s", name)

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self, category: Optional[str] = None) -> List[Tool]:
        """List all tools, optionally filtered by category."""
        if category:
            names = self._categories.get(category, [])
            return [self._tools[n] for n in names if n in self._tools]
        return list(self._tools.values())

    def list_categories(self) -> List[str]:
        """List all tool categories."""
        return list(self._categories.keys())

    def get_openai_tools(self, categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get tools in OpenAI function-calling format."""
        tools = self.list_tools()
        if categories:
            tools = [t for t in tools if t.category in categories]
        return [t.to_openai_schema() for t in tools]

    def get_anthropic_tools(self, categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get tools in Anthropic tool format."""
        tools = self.list_tools()
        if categories:
            tools = [t for t in tools if t.category in categories]
        return [t.to_anthropic_schema() for t in tools]

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool by name with the given arguments."""
        tool = self.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found"
        return await tool.execute(**arguments)

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            "total_tools": len(self._tools),
            "categories": {cat: len(names) for cat, names in self._categories.items()},
        }


# Global tool registry
tool_registry = ToolRegistry()


# ──────────────────────────────────────────
# Built-in Tool Handlers
# ──────────────────────────────────────────

async def web_search_tool(query: str) -> str:
    """Search the web for information."""
    # Placeholder — integrate with a search API
    return f"Search results for '{query}' would appear here."


async def calculator_tool(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        # Safe evaluation
        allowed = {"abs", "int", "float", "str", "len", "range",
                   "min", "max", "sum", "pow", "round"}
        result = eval(expression, {"__builtins__": {}}, {k: __builtins__[k] for k in allowed if k in __builtins__})
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"


async def current_time_tool(timezone_str: str = "UTC") -> str:
    """Get the current time."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    return f"Current UTC time: {now.isoformat()}"


def register_builtin_tools():
    """Register built-in tools with the global registry."""
    tool_registry.register_many([
        Tool(
            name="web_search",
            description="Search the web for current information",
            handler=web_search_tool,
            parameters={
                "query": {
                    "type": "string",
                    "description": "The search query",
                }
            },
            required=["query"],
            category="web",
        ),
        Tool(
            name="calculator",
            description="Evaluate a mathematical expression",
            handler=calculator_tool,
            parameters={
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to evaluate",
                }
            },
            required=["expression"],
            category="general",
        ),
        Tool(
            name="current_time",
            description="Get the current date and time",
            handler=current_time_tool,
            parameters={
                "timezone_str": {
                    "type": "string",
                    "description": "Timezone (default: UTC)",
                }
            },
            category="general",
        ),
    ])
