"""
Zentar Intelligence — Memory Service

Long-term memory management with semantic search, tagging,
and importance-based retrieval for the AI assistant.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.services.embedding_service import embedding_service

logger = logging.getLogger("zentar.services.memory")

settings = get_settings()


class MemoryEntry:
    """A single memory entry with metadata."""

    def __init__(
        self,
        memory_id: str,
        content: str,
        memory_type: str = "conversation",  # conversation, long_term, project, pinned, note
        scope: str = "private",  # private, shared, project
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        project_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.memory_id = memory_id
        self.content = content
        self.memory_type = memory_type
        self.scope = scope
        self.tags = tags or []
        self.importance = max(0.0, min(1.0, importance))
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.project_id = project_id
        self.metadata = metadata or {}
        self.created_at = time.time()
        self.updated_at = time.time()
        self.recall_count = 0
        self.last_recalled: Optional[float] = None
        self.embedding: Optional[List[float]] = None

    def recall(self):
        """Increment recall counter and update timestamp."""
        self.recall_count += 1
        self.last_recalled = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "memory_type": self.memory_type,
            "scope": self.scope,
            "tags": self.tags,
            "importance": self.importance,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "project_id": self.project_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "recall_count": self.recall_count,
            "last_recalled": self.last_recalled,
        }


class MemoryService:
    """Long-term memory management with semantic search capabilities."""

    def __init__(self):
        self._memories: Dict[str, MemoryEntry] = {}
        self._max_memories = 10000

    async def store(
        self,
        content: str,
        memory_type: str = "conversation",
        scope: str = "private",
        tags: Optional[List[str]] = None,
        importance: float = 0.5,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        project_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> MemoryEntry:
        """Store a new memory entry."""
        import uuid
        memory = MemoryEntry(
            memory_id=str(uuid.uuid4()),
            content=content,
            memory_type=memory_type,
            scope=scope,
            tags=tags,
            importance=importance,
            user_id=user_id,
            conversation_id=conversation_id,
            project_id=project_id,
            metadata=metadata,
        )

        # Generate embedding
        try:
            memory.embedding = await embedding_service.embed_text(content)
        except Exception as e:
            logger.warning("Failed to generate embedding: %s", e)

        # Enforce memory limit
        if len(self._memories) >= self._max_memories:
            oldest = min(self._memories.values(), key=lambda m: m.importance)
            del self._memories[oldest.memory_id]

        self._memories[memory.memory_id] = memory
        logger.info("Stored memory: %s (type=%s, importance=%.2f)", memory.memory_id[:8], memory_type, importance)
        return memory

    async def search(
        self,
        query: str,
        memory_type: Optional[str] = None,
        scope: Optional[str] = None,
        tags: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        limit: int = 10,
        min_importance: float = 0.0,
    ) -> List[MemoryEntry]:
        """Search memories by semantic similarity and filters.

        Uses a hybrid approach: semantic similarity + keyword + filters.
        """
        # Generate query embedding
        query_embedding = await embedding_service.embed_text(query)

        # Score all memories
        scored = []
        for memory in self._memories.values():
            # Apply filters
            if memory_type and memory.memory_type != memory_type:
                continue
            if scope and memory.scope != scope:
                continue
            if user_id and memory.user_id != user_id:
                continue
            if tags and not all(t in memory.tags for t in tags):
                continue
            if memory.importance < min_importance:
                continue

            # Compute similarity score
            similarity = 0.0
            if memory.embedding:
                similarity = embedding_service.cosine_similarity(query_embedding, memory.embedding)

            # Boost by importance
            score = similarity * 0.7 + memory.importance * 0.3
            scored.append((score, memory))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [m for _, m in scored[:limit]]

        # Update recall stats
        for m in results:
            m.recall()

        return results

    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get a specific memory by ID."""
        memory = self._memories.get(memory_id)
        if memory:
            memory.recall()
        return memory

    def delete(self, memory_id: str) -> bool:
        """Delete a memory."""
        if memory_id in self._memories:
            del self._memories[memory_id]
            return True
        return False

    def update_importance(self, memory_id: str, importance: float) -> bool:
        """Update the importance score of a memory."""
        memory = self._memories.get(memory_id)
        if not memory:
            return False
        memory.importance = max(0.0, min(1.0, importance))
        memory.updated_at = time.time()
        return True

    def list_memories(
        self,
        memory_type: Optional[str] = None,
        scope: Optional[str] = None,
        tags: Optional[List[str]] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[MemoryEntry]:
        """List memories with pagination and filters."""
        memories = list(self._memories.values())

        if memory_type:
            memories = [m for m in memories if m.memory_type == memory_type]
        if scope:
            memories = [m for m in memories if m.scope == scope]
        if user_id:
            memories = [m for m in memories if m.user_id == user_id]
        if tags:
            memories = [m for m in memories if all(t in m.tags for t in tags)]

        memories.sort(key=lambda m: m.importance, reverse=True)
        return memories[offset:offset + limit]

    def count(
        self,
        memory_type: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> int:
        """Count memories matching filters."""
        memories = self._memories.values()
        if memory_type:
            memories = [m for m in memories if m.memory_type == memory_type]
        if user_id:
            memories = [m for m in memories if m.user_id == user_id]
        return len(memories)

    def get_stats(self) -> Dict[str, Any]:
        """Get memory service statistics."""
        types = {}
        for m in self._memories.values():
            types[m.memory_type] = types.get(m.memory_type, 0) + 1
        return {
            "total_memories": len(self._memories),
            "max_memories": self._max_memories,
            "types": types,
            "avg_importance": (
                sum(m.importance for m in self._memories.values()) / len(self._memories)
                if self._memories else 0
            ),
        }


# Global memory service
memory_service = MemoryService()
