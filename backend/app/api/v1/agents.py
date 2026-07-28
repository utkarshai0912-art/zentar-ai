"""
Zentar Intelligence — Agent API Routes

Endpoints for agent configuration, execution, and management.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.agent_engine import AgentEngine, agent_manager
from app.agents.coding_agent import coding_agent_manager
from app.core.security import get_current_user

logger = logging.getLogger("zentar.api.agents")
router = APIRouter(prefix="/agents", tags=["agents"])


# ──────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────

class CreateAgentRequest(BaseModel):
    name: str = "Zentar Assistant"
    system_prompt: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    tool_categories: Optional[list[str]] = None
    enable_tools: bool = True
    memory_enabled: bool = True


class AgentMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=100000)
    conversation_id: Optional[str] = None
    stream: bool = True


# ──────────────────────────────────────────
# Routes
# ──────────────────────────────────────────

@router.post("")
async def create_agent(
    request: CreateAgentRequest,
    user_id: str = Depends(get_current_user),
):
    """Create a new agent instance."""
    engine = agent_manager.create_agent(
        name=request.name,
        system_prompt=request.system_prompt,
        provider=request.provider,
        model=request.model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        tool_categories=request.tool_categories,
        enable_tools=request.enable_tools,
        memory_enabled=request.memory_enabled,
    )
    return {
        "success": True,
        "data": {
            "agent_id": engine.config.agent_id,
            "name": engine.config.name,
            "provider": engine.config.provider,
            "model": engine.config.model,
        },
    }


@router.get("")
async def list_agents(
    user_id: str = Depends(get_current_user),
):
    """List all active agents."""
    return {
        "success": True,
        "data": agent_manager.list_agents(),
    }


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    user_id: str = Depends(get_current_user),
):
    """Get agent details and stats."""
    engine = agent_manager.get_agent(agent_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "success": True,
        "data": engine.get_stats(),
    }


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    user_id: str = Depends(get_current_user),
):
    """Delete an agent instance."""
    agent_manager.delete_agent(agent_id)
    coding_agent_manager.delete(agent_id)
    return {"success": True, "message": "Agent deleted"}


@router.post("/{agent_id}/chat")
async def agent_chat(
    agent_id: str,
    request: AgentMessageRequest,
    user_id: str = Depends(get_current_user),
):
    """Send a message to an agent and get a response."""
    engine = agent_manager.get_agent(agent_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Agent not found")

    async def event_stream():
        async for event in engine.execute(
            message=request.message,
            conversation_id=request.conversation_id,
            stream=request.stream,
        ):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ──────────────────────────────────────────
# Coding Agent Routes
# ──────────────────────────────────────────

@router.post("/coding")
async def create_coding_agent(
    user_id: str = Depends(get_current_user),
):
    """Create a coding agent with workspace."""
    import uuid
    agent_id = str(uuid.uuid4())
    agent = await coding_agent_manager.get_or_create(agent_id)
    return {
        "success": True,
        "data": {
            "agent_id": agent_id,
            "workspace_path": agent.workspace.path,
        },
    }


@router.post("/coding/{agent_id}/chat")
async def coding_agent_chat(
    agent_id: str,
    request: AgentMessageRequest,
    user_id: str = Depends(get_current_user),
):
    """Send a message to a coding agent."""
    agent = coding_agent_manager.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Coding agent not found")

    async def event_stream():
        async for event in agent.execute(
            message=request.message,
            conversation_id=request.conversation_id,
            stream=request.stream,
        ):
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/coding/workspaces")
async def list_workspaces(
    user_id: str = Depends(get_current_user),
):
    """List all coding agent workspaces."""
    return {
        "success": True,
        "data": coding_agent_manager.list_workspaces(),
    }


@router.get("/tools")
async def list_tools(
    category: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user),
):
    """List available tools."""
    from app.agents.tool_registry import tool_registry
    tools = tool_registry.list_tools(category)
    return {
        "success": True,
        "data": {
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "category": t.category,
                    "parameters": t.parameters,
                }
                for t in tools
            ],
            "categories": tool_registry.list_categories(),
        },
    }


@router.get("/stats")
async def agent_stats(
    user_id: str = Depends(get_current_user),
):
    """Get agent system statistics."""
    stats = agent_manager.get_stats()
    return {"success": True, "data": stats}
