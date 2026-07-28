"""
Zentar Intelligence — Per-Agent Memory System

Multi-tier memory: short-term (conversation), long-term (persistent),
project-scoped, semantic (embedding-based), and knowledge retrieval.
"""

import logging
import time
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("zentar.agents.agent_memory")


class ShortTermMemory:
    def __init__(self, max_items: int = 50):
        self._items: List[Dict[str, Any]] = []
        self._max_items = max_items

    def add(self, role: str, content: str, metadata: Optional[Dict] = None):
        self._items.append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "metadata": metadata or {},
        })
        if len(self._items) > self._max_items:
            self._items.pop(0)

    def get_recent(self, n: int = 10) -> List[Dict[str, Any]]:
        return self._items[-n:]

    def search(self, query: str) -> List[Dict[str, Any]]:
        q = query.lower()
        return [item for item in self._items if q in item["content"].lower()]

    def clear(self):
        self._items.clear()


class LongTermMemory:
    def __init__(self):
        self._memories: Dict[str, Dict[str, Any]] = {}
        self._max_memories = 1000

    def store(self, key: str, content: str, importance: float = 0.5,
              tags: Optional[List[str]] = None, context: Optional[Dict] = None):
        if key in self._memories:
            existing = self._memories[key]
            existing["content"] = content
            existing["importance"] = max(existing["importance"], importance)
            existing["access_count"] = existing.get("access_count", 0)
            existing["updated_at"] = time.time()
            if tags:
                existing["tags"] = list(set(existing.get("tags", []) + tags))
            return

        self._memories[key] = {
            "key": key,
            "content": content,
            "importance": importance,
            "tags": tags or [],
            "context": context or {},
            "access_count": 0,
            "created_at": time.time(),
            "updated_at": time.time(),
        }

        if len(self._memories) > self._max_memories:
            self._evict()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        memory = self._memories.get(key)
        if memory:
            memory["access_count"] += 1
            memory["last_accessed"] = time.time()
        return memory

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        q = query.lower()
        scored = []
        for mem in self._memories.values():
            score = 0
            if q in mem["content"].lower():
                score += mem["importance"] * 2
            for tag in mem.get("tags", []):
                if q in tag.lower():
                    score += 0.5
            if score > 0:
                scored.append((score, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:limit]]

    def update_importance(self, key: str, delta: float):
        mem = self._memories.get(key)
        if mem:
            mem["importance"] = max(0, min(1.0, mem["importance"] + delta))

    def delete(self, key: str):
        self._memories.pop(key, None)

    def _evict(self):
        oldest = min(self._memories.values(),
                    key=lambda m: (m["importance"], m.get("access_count", 0)))
        del self._memories[oldest["key"]]
        logger.info("Evicted low-importance memory: %s", oldest["key"])


class ProjectMemory:
    def __init__(self):
        self._projects: Dict[str, Dict[str, Any]] = defaultdict(dict)

    def store(self, project_id: str, key: str, content: str,
              metadata: Optional[Dict] = None):
        if project_id not in self._projects:
            self._projects[project_id] = {"_metadata": {"created_at": time.time()}}
        self._projects[project_id][key] = {
            "content": content,
            "metadata": metadata or {},
            "timestamp": time.time(),
        }

    def get(self, project_id: str, key: str) -> Optional[str]:
        project = self._projects.get(project_id)
        if project:
            item = project.get(key)
            return item["content"] if item else None
        return None

    def get_all(self, project_id: str) -> Dict[str, Any]:
        return {k: v for k, v in self._projects.get(project_id, {}).items()
                if not k.startswith("_")}

    def delete_project(self, project_id: str):
        self._projects.pop(project_id, None)


class SemanticMemory:
    def __init__(self):
        self._entries: List[Dict[str, Any]] = []
        self._max_entries = 5000

    def store(self, content: str, embedding: List[float],
              metadata: Optional[Dict] = None):
        self._entries.append({
            "content": content,
            "embedding": embedding,
            "metadata": metadata or {},
            "timestamp": time.time(),
        })
        if len(self._entries) > self._max_entries:
            self._entries.pop(0)

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        if not self._entries:
            return []
        scored = []
        for entry in self._entries:
            score = self._cosine_similarity(query_embedding, entry["embedding"])
            scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"content": e["content"], "score": s, **e["metadata"]}
                for s, e in scored[:top_k]]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if not norm_a or not norm_b:
            return 0.0
        return dot / (norm_a * norm_b)


class AgentMemory:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        self.project = ProjectMemory()
        self.semantic = SemanticMemory()
        self._conversation_history: List[Dict[str, Any]] = []

    def remember_conversation(self, role: str, content: str):
        self._conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
        })
        self.short_term.add(role, content)

    def get_conversation_context(self, n: int = 20) -> List[Dict[str, Any]]:
        return self._conversation_history[-n:]

    def store_knowledge(self, key: str, content: str, importance: float = 0.5,
                        tags: Optional[List[str]] = None):
        self.long_term.store(key, content, importance, tags)

    def retrieve_knowledge(self, query: str) -> List[Dict[str, Any]]:
        results = self.short_term.search(query)
        results.extend(self.long_term.search(query))
        return results

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "short_term_items": len(self.short_term._items),
            "long_term_items": len(self.long_term._memories),
            "conversation_length": len(self._conversation_history),
            "semantic_entries": len(self.semantic._entries),
        }


class AgentMemoryManager:
    def __init__(self):
        self._memories: Dict[str, AgentMemory] = {}

    def get_or_create(self, agent_id: str) -> AgentMemory:
        if agent_id not in self._memories:
            self._memories[agent_id] = AgentMemory(agent_id)
        return self._memories[agent_id]

    def delete(self, agent_id: str):
        self._memories.pop(agent_id, None)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_agents": len(self._memories),
            "total_short_term": sum(len(m.short_term._items) for m in self._memories.values()),
            "total_long_term": sum(len(m.long_term._memories) for m in self._memories.values()),
        }


agent_memory_manager = AgentMemoryManager()