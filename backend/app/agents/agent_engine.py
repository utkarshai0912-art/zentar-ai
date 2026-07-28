"""
Zentar Intelligence — Agent Engine

Core orchestrator that ties together memory, tools, prompts,
and context management for AI agent execution.
"""

import json
import logging
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from app.agents.context_manager import context_manager
from app.agents.memory_manager import ConversationMemory, memory_manager
from app.agents.prompt_engine import PromptLibrary, SystemPromptBuilder
from app.agents.tool_registry import Tool, ToolRegistry, register_builtin_tools, tool_registry
from app.core.config import get_settings
from app.services.ai_service import count_tokens, provider_registry

logger = logging.getLogger("zentar.agents.engine")

settings = get_settings()

# Initialize built-in tools
register_builtin_tools()


class AgentConfig:
    """Configuration for an agent instance."""

    def __init__(
        self,
        agent_id: str,
        name: str = "Zentar Assistant",
        system_prompt: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tool_categories: Optional[List[str]] = None,
        enable_tools: bool = True,
        memory_enabled: bool = True,
        skills: Optional[List[str]] = None,
    ):
        self.agent_id = agent_id
        self.name = name
        self.system_prompt = system_prompt
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.tool_categories = tool_categories or ["general", "web"]
        self.enable_tools = enable_tools
        self.memory_enabled = memory_enabled
        self.skills = skills or []


class AgentEngine:
    """Core agent engine — orchestrates memory, tools, prompts, and AI."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self._memory: Optional[ConversationMemory] = None
        self._current_conversation_id: Optional[str] = None

    async def execute(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        stream: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute a complete agent turn — process input, build context, call AI, handle tools."""
        conv_id = conversation_id or str(uuid.uuid4())
        self._current_conversation_id = conv_id

        # Set up memory
        if self.config.memory_enabled:
            self._memory = memory_manager.get_or_create(conv_id)
            if self.config.system_prompt:
                self._memory.set_system_prompt(self.config.system_prompt)
            self._memory.add_message("user", message)
        else:
            self._memory = ConversationMemory(conv_id)
            if self.config.system_prompt:
                self._memory.set_system_prompt(self.config.system_prompt)
            self._memory.add_message("user", message)

        # Build context
        messages = self._build_context()

        # Check if summarization is needed
        if self._memory.needs_summarization():
            logger.info("Summarizing conversation %s", conv_id)
            await self._memory.summarize(self.config.provider)
            messages = self._build_context()

        # Get available tools
        tools = None
        if self.config.enable_tools:
            tools = tool_registry.get_openai_tools(self.config.tool_categories)

        # Call AI
        async for event in self._call_ai(messages, tools, stream):
            if event["type"] == "tool_call" and self.config.enable_tools:
                # Execute tool and continue
                result = await self._handle_tool_call(event)
                if self.config.memory_enabled:
                    self._memory.add_message("assistant", event.get("content", ""))
                    self._memory.add_message("tool", result)
                # Stream tool result
                yield {
                    "type": "tool_result",
                    "tool_name": event.get("tool_name", ""),
                    "content": result,
                    "conversation_id": conv_id,
                }
                # Continue with tool result fed back
                messages = self._build_context()
                if tools:
                    messages[-1]["tool_results"] = result
                async for cont_event in self._call_ai(messages, tools, stream):
                    if cont_event["type"] == "done":
                        if self.config.memory_enabled:
                            self._memory.add_message(
                                "assistant",
                                cont_event.get("content", ""),
                            )
                    yield cont_event
            elif event["type"] == "done":
                if self.config.memory_enabled:
                    self._memory.add_message(
                        "assistant",
                        event.get("content", ""),
                    )
                yield event
            else:
                yield event

    def _build_context(self) -> List[Dict[str, str]]:
        """Build optimized context from memory."""
        if not self._memory:
            return []

        messages = self._memory.get_context_window()

        # Optimize context if needed
        model = self.config.model or "gpt-4o"
        if context_manager.estimate_tokens(messages) > 100000:
            messages = context_manager.optimize(messages, model=model)

        return messages

    async def _call_ai(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        stream: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Call the AI provider with built context."""
        max_tokens = self.config.max_tokens
        if tools:
            max_tokens = min(max_tokens, 8192)  # Reserve tokens for tool use

        async for event in provider_registry.route_request(
            messages=messages,
            provider_name=self.config.provider,
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=max_tokens,
            stream=stream,
        ):
            yield event

    async def _handle_tool_call(self, event: Dict[str, Any]) -> str:
        """Handle a tool call from the AI."""
        tool_name = event.get("tool_name", "")
        arguments = event.get("arguments", {})

        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                return f"Error: Invalid tool arguments JSON"

        return await tool_registry.execute_tool(tool_name, arguments)

    def get_stats(self) -> Dict[str, Any]:
        """Get agent engine statistics."""
        return {
            "agent_id": self.config.agent_id,
            "name": self.config.name,
            "provider": self.config.provider,
            "model": self.config.model,
            "tools_enabled": self.config.enable_tools,
            "memory_enabled": self.config.memory_enabled,
            "conversation_id": self._current_conversation_id,
        }


class AgentManager:
    """Manages multiple agent instances and their configurations."""

    def __init__(self):
        self._agents: Dict[str, AgentEngine] = {}
        self._configs: Dict[str, AgentConfig] = {}

    def create_agent(
        self,
        name: str = "Zentar Assistant",
        system_prompt: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tool_categories: Optional[List[str]] = None,
        enable_tools: bool = True,
        memory_enabled: bool = True,
        skills: Optional[List[str]] = None,
    ) -> AgentEngine:
        """Create a new agent instance."""
        agent_id = str(uuid.uuid4())
        config = AgentConfig(
            agent_id=agent_id,
            name=name,
            system_prompt=system_prompt,
            provider=provider,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tool_categories=tool_categories,
            enable_tools=enable_tools,
            memory_enabled=memory_enabled,
            skills=skills,
        )
        self._configs[agent_id] = config
        engine = AgentEngine(config)
        self._agents[agent_id] = engine
        return engine

    def get_agent(self, agent_id: str) -> Optional[AgentEngine]:
        """Get an existing agent by ID."""
        return self._agents.get(agent_id)

    def delete_agent(self, agent_id: str):
        """Delete an agent instance."""
        self._agents.pop(agent_id, None)
        self._configs.pop(agent_id, None)

    def list_agents(self) -> List[Dict[str, Any]]:
        """List all active agents."""
        return [
            {
                "agent_id": aid,
                "name": cfg.name,
                "provider": cfg.provider,
                "model": cfg.model,
                "tools_enabled": cfg.enable_tools,
                "memory_enabled": cfg.memory_enabled,
            }
            for aid, cfg in self._configs.items()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get agent manager statistics."""
        return {
            "active_agents": len(self._agents),
            "tool_stats": tool_registry.get_stats(),
            "memory_stats": memory_manager.get_stats(),
        }


# Global agent manager
agent_manager = AgentManager()
