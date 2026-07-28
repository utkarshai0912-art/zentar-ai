"""
Zentar Intelligence — Background Task Definitions

Background task definitions for async operations like notifications,
data export, and long-running AI operations.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from app.core.config import get_settings

logger = logging.getLogger("zentar.workers.tasks")

settings = get_settings()


class Task:
    """A background task with progress tracking."""

    def __init__(
        self,
        task_id: str,
        name: str,
        task_type: str,
        params: Optional[Dict[str, Any]] = None,
    ):
        self.task_id = task_id
        self.name = name
        self.task_type = task_type
        self.params = params or {}
        self.status = "pending"  # pending, running, completed, failed
        self.progress: float = 0.0
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.created_at = asyncio.get_event_loop().time()
        self.completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "type": self.task_type,
            "status": self.status,
            "progress": self.progress,
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class TaskQueue:
    """In-memory task queue for background operations."""

    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._max_tasks = 1000

    def enqueue(self, task: Task):
        """Add a task to the queue."""
        self._tasks[task.task_id] = task
        if len(self._tasks) > self._max_tasks:
            # Remove oldest completed task
            completed = [t for t in self._tasks.values() if t.status in ("completed", "failed")]
            if completed:
                oldest = min(completed, key=lambda t: t.completed_at or 0)
                del self._tasks[oldest.task_id]
        logger.info("Task enqueued: %s (%s)", task.name, task.task_id[:8])

    def get(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def update(self, task_id: str, **kwargs):
        """Update task properties."""
        task = self._tasks.get(task_id)
        if task:
            for key, value in kwargs.items():
                setattr(task, key, value)
            if kwargs.get("status") in ("completed", "failed"):
                task.completed_at = asyncio.get_event_loop().time()

    def list_tasks(
        self,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Task]:
        """List tasks with optional filtering."""
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]

    def cleanup_old(self, max_age_seconds: int = 3600):
        """Remove tasks older than max_age."""
        now = asyncio.get_event_loop().time()
        self._tasks = {
            tid: t for tid, t in self._tasks.items()
            if t.status in ("pending", "running") or (now - (t.completed_at or now)) < max_age_seconds
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        statuses = {}
        for t in self._tasks.values():
            statuses[t.status] = statuses.get(t.status, 0) + 1
        return {
            "total": len(self._tasks),
            "statuses": statuses,
        }


# Global task queue
task_queue = TaskQueue()


# ──────────────────────────────────────────
# Background Task Handlers
# ──────────────────────────────────────────

async def run_export_task(task_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Run a data export task."""
    export_type = params.get("type", "conversations")
    format = params.get("format", "json")
    user_id = params.get("user_id")

    logger.info("Export task %s: type=%s, format=%s", task_id[:8], export_type, format)
    task_queue.update(task_id, status="running", progress=0.1)

    try:
        # Simulate export (in production, query DB and serialize)
        await asyncio.sleep(2)
        task_queue.update(task_id, progress=0.5)

        export_data = {
            "type": export_type,
            "format": format,
            "exported_at": asyncio.get_event_loop().time(),
            "items": [],
        }

        await asyncio.sleep(1)
        task_queue.update(task_id, progress=1.0, status="completed", result=export_data)
        return export_data

    except Exception as e:
        task_queue.update(task_id, status="failed", error=str(e))
        raise


async def run_ai_batch_task(task_id: str, params: Dict[str, Any]) -> str:
    """Run a batch AI processing task."""
    prompt = params.get("prompt", "")
    items = params.get("items", [])

    task_queue.update(task_id, status="running", progress=0.0)
    results = []

    for i, item in enumerate(items):
        # Process each item
        results.append(f"Processed: {item}")
        progress = (i + 1) / len(items)
        task_queue.update(task_id, progress=progress)
        await asyncio.sleep(0.5)  # Simulate processing

    task_queue.update(task_id, status="completed", result=results)
    return json.dumps(results)


async def run_cleanup_task(task_id: str, params: Dict[str, Any]) -> str:
    """Run a cleanup operation."""
    target = params.get("target", "all")
    task_queue.update(task_id, status="running", progress=0.0)

    if target in ("sessions", "all"):
        from app.mcp.auth import mcp_auth_provider
        mcp_auth_provider.cleanup_expired()
        task_queue.update(task_id, progress=0.3)

    if target in ("memory", "all"):
        from app.agents.memory_manager import memory_manager
        memory_manager.cleanup_inactive(max_age_minutes=60)
        task_queue.update(task_id, progress=0.6)

    if target in ("cache", "all"):
        from app.services.embedding_service import embedding_service
        embedding_service.clear_cache()
        task_queue.update(task_id, progress=1.0)

    task_queue.update(task_id, status="completed")
    return f"Cleanup of '{target}' completed"
