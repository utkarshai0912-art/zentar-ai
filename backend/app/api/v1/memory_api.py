"""
Zentar Intelligence — Memory API Routes

Endpoints for long-term memory management with semantic search.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.services.memory_service import memory_service

logger = logging.getLogger("zentar.api.memory")
router = APIRouter(prefix="/memory", tags=["memory"])


# ──────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────

class StoreMemoryRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=50000)
    memory_type: str = "conversation"
    scope: str = "private"
    tags: Optional[List[str]] = None
    importance: float = 0.5
    conversation_id: Optional[str] = None
    project_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SearchMemoryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    memory_type: Optional[str] = None
    scope: Optional[str] = None
    tags: Optional[List[str]] = None
    limit: int = 10
    min_importance: float = 0.0


# ──────────────────────────────────────────
# Routes
# ──────────────────────────────────────────

@router.post("")
async def store_memory(
    request: StoreMemoryRequest,
    user_id: str = Depends(get_current_user),
):
    """Store a new memory entry."""
    memory = await memory_service.store(
        content=request.content,
        memory_type=request.memory_type,
        scope=request.scope,
        tags=request.tags,
        importance=request.importance,
        user_id=user_id,
        conversation_id=request.conversation_id,
        project_id=request.project_id,
        metadata=request.metadata,
    )
    return {"success": True, "data": memory.to_dict()}


@router.post("/search")
async def search_memories(
    request: SearchMemoryRequest,
    user_id: str = Depends(get_current_user),
):
    """Semantic search through memories."""
    results = await memory_service.search(
        query=request.query,
        memory_type=request.memory_type,
        scope=request.scope,
        tags=request.tags,
        user_id=user_id,
        limit=request.limit,
        min_importance=request.min_importance,
    )
    return {
        "success": True,
        "data": {
            "results": [m.to_dict() for m in results],
            "total": len(results),
        },
    }


@router.get("")
async def list_memories(
    memory_type: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user),
):
    """List memories with filters and pagination."""
    tag_list = tags.split(",") if tags else None
    memories = memory_service.list_memories(
        memory_type=memory_type,
        scope=scope,
        tags=tag_list,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )
    total = memory_service.count(memory_type=memory_type, user_id=user_id)
    return {
        "success": True,
        "data": {
            "memories": [m.to_dict() for m in memories],
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


@router.get("/{memory_id}")
async def get_memory(
    memory_id: str,
    user_id: str = Depends(get_current_user),
):
    """Get a specific memory."""
    memory = memory_service.get(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"success": True, "data": memory.to_dict()}


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    user_id: str = Depends(get_current_user),
):
    """Delete a memory."""
    success = memory_service.delete(memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"success": True, "message": "Memory deleted"}


@router.put("/{memory_id}/importance")
async def update_importance(
    memory_id: str,
    importance: float,
    user_id: str = Depends(get_current_user),
):
    """Update memory importance score."""
    success = memory_service.update_importance(memory_id, importance)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"success": True, "message": "Importance updated"}


@router.get("/stats")
async def memory_stats(
    user_id: str = Depends(get_current_user),
):
    """Get memory service statistics."""
    return {"success": True, "data": memory_service.get_stats()}
