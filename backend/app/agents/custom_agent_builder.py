"""
Zentar Intelligence — Custom Agent Builder

Allows users to build their own agents with custom name, avatar, role,
system prompt, model, temperature, memory, permissions, knowledge sources,
and available tools.
"""

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from app.agents.agent_engine import AgentConfig, AgentEngine, agent_manager
from app.services.ai_service import provider_registry

logger = logging.getLogger("zentar.agents.custom")


class CustomAgentDefinition:
    """Definition of a user-created custom agent."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        role: str,
        system_prompt: str,
        avatar: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        memory_enabled: bool = True,
        permissions: Optional[List[str]] = None,
        knowledge_sources: Optional[List[str]] = None,
        allowed_tools: Optional[List[str]] = None,
    ):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.avatar = avatar
        self.model = model
        self.provider = provider
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.memory_enabled = memory_enabled
        self.permissions = permissions or []
        self.knowledge_sources = knowledge_sources or []
        self.allowed_tools = allowed_tools or []
        self.is_active = False
        self.created_at = time.time()
        self.updated_at = time.time()
        self.total_conversations = 0
        self.total_tokens_used = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "avatar": self.avatar,
            "model": self.model,
            "provider": self.provider,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "memory_enabled": self.memory_enabled,
            "permissions": self.permissions,
            "knowledge_sources": self.knowledge_sources,
            "allowed_tools": self.allowed_tools,
            "is_active": self.is_active,
            "total_conversations": self.total_conversations,
            "total_tokens_used": self.total_tokens_used,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class CustomAgentBuilder:
    """Manages custom agent creation and lifecycle."""

    def __init__(self):
        self._agents: Dict[str, CustomAgentDefinition] = {}
        self._running_engines: Dict[str, str] = {}  # agent_id -> engine_id

    def create_agent(
        self,
        name: str,
        role: str,
        system_prompt: str,
        avatar: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        memory_enabled: bool = True,
        permissions: Optional[List[str]] = None,
        knowledge_sources: Optional[List[str]] = None,
        allowed_tools: Optional[List[str]] = None,
    ) -> CustomAgentDefinition:
        agent_id = str(uuid.uuid4())
        agent = CustomAgentDefinition(
            agent_id=agent_id,
            name=name,
            role=role,
            system_prompt=system_prompt,
            avatar=avatar,
            model=model,
            provider=provider,
            temperature=temperature,
            max_tokens=max_tokens,
            memory_enabled=memory_enabled,
            permissions=permissions,
            knowledge_sources=knowledge_sources,
            allowed_tools=allowed_tools,
        )
        self._agents[agent_id] = agent
        logger.info("Created custom agent: %s (%s)", name, agent_id[:8])
        return agent

    def get_agent(self, agent_id: str) -> Optional[CustomAgentDefinition]:
        return self._agents.get(agent_id)

    def update_agent(self, agent_id: str, **kwargs) -> Optional[CustomAgentDefinition]:
        agent = self._agents.get(agent_id)
        if not agent:
            return None
        for key, value in kwargs.items():
            if hasattr(agent, key) and value is not None:
                setattr(agent, key, value)
        agent.updated_at = time.time()
        return agent

    def delete_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            self._running_engines.pop(agent_id, None)
            return True
        return False

    def activate_agent(self, agent_id: str) -> bool:
        agent = self._agents.get(agent_id)
        if not agent:
            return False
        engine = agent_manager.create_agent(
            name=agent.name,
            system_prompt=agent.system_prompt,
            provider=agent.provider,
            model=agent.model,
            temperature=agent.temperature,
            max_tokens=agent.max_tokens,
            memory_enabled=agent.memory_enabled,
            tool_categories=agent.allowed_tools or None,
        )
        self._running_engines[agent_id] = engine.config.agent_id
        agent.is_active = True
        return True

    def deactivate_agent(self, agent_id: str) -> bool:
        engine_id = self._running_engines.pop(agent_id, None)
        if engine_id:
            agent_manager.delete_agent(engine_id)
        agent = self._agents.get(agent_id)
        if agent:
            agent.is_active = False
        return True

    def list_agents(self) -> List[Dict[str, Any]]:
        return [a.to_dict() for a in self._agents.values()]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_agents": len(self._agents),
            "active_agents": len(self._running_engines),
        }


custom_agent_builder = CustomAgentBuilder()