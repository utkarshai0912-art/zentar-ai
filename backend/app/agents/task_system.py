"""
Zentar Intelligence — Enterprise Task System

Full-featured task management with priority, dependencies, retry,
confidence scoring, and execution tracking.
"""

import asyncio
import logging
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable

logger = logging.getLogger("zentar.agents.tasks")


class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class Task:
    def __init__(
        self,
        task_id: str,
        name: str,
        task_type: str,
        params: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        dependencies: Optional[List[str]] = None,
        max_retries: int = 3,
        assigned_agent: Optional[str] = None,
        assigned_manager: Optional[str] = None,
        assigned_ceo: Optional[str] = None,
        confidence_score: float = 0.0,
        timeout_seconds: Optional[int] = None,
    ):
        self.task_id = task_id
        self.name = name
        self.task_type = task_type
        self.params = params or {}
        self.priority = priority
        self.dependencies = dependencies or []
        self.max_retries = max_retries
        self.retry_count = 0
        self.assigned_agent = assigned_agent
        self.assigned_manager = assigned_manager
        self.assigned_ceo = assigned_ceo
        self.confidence_score = confidence_score
        self.timeout_seconds = timeout_seconds
        self.status = TaskStatus.PENDING
        self.progress: float = 0.0
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.logs: List[Dict[str, Any]] = None
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.execution_time: Optional[float] = None
        self._init_logs()

    def _init_logs(self):
        self.logs = [{"timestamp": self.created_at, "level": "INFO", "message": f"Task '{self.name}' created"}]

    def add_log(self, level: str, message: str):
        self.logs.append({"timestamp": time.time(), "level": level, "message": message})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "type": self.task_type,
            "priority": self.priority.name,
            "status": self.status.value,
            "progress": self.progress,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "assigned_agent": self.assigned_agent,
            "assigned_manager": self.assigned_manager,
            "confidence_score": self.confidence_score,
            "dependencies": self.dependencies,
            "error": self.error,
            "logs": self.logs[-10:],
            "execution_time": self.execution_time,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class TaskOrchestrator:
    def __init__(self, max_concurrent: int = 20):
        self._tasks: Dict[str, Task] = {}
        self._handlers: Dict[str, Callable] = {}
        self._running: Dict[str, asyncio.Task] = {}
        self._max_concurrent = max_concurrent
        self._max_tasks = 5000

    def register_handler(self, task_type: str, handler: Callable[[Task], Awaitable[Any]]):
        self._handlers[task_type] = handler

    def create_task(
        self,
        name: str,
        task_type: str,
        params: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        dependencies: Optional[List[str]] = None,
        max_retries: int = 3,
        assigned_agent: Optional[str] = None,
        assigned_manager: Optional[str] = None,
        assigned_ceo: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> Task:
        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            name=name,
            task_type=task_type,
            params=params,
            priority=priority,
            dependencies=dependencies or [],
            max_retries=max_retries,
            assigned_agent=assigned_agent,
            assigned_manager=assigned_manager,
            assigned_ceo=assigned_ceo,
            timeout_seconds=timeout_seconds,
        )
        self._tasks[task_id] = task

        if task.dependencies:
            deps_met = all(
                dep in self._tasks and self._tasks[dep].status == TaskStatus.COMPLETED
                for dep in task.dependencies
            )
            if not deps_met:
                task.status = TaskStatus.BLOCKED
                task.add_log("WARNING", "Task blocked by unmet dependencies")

        if len(self._tasks) > self._max_tasks:
            completed = [t for t in self._tasks.values()
                        if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED)]
            completed.sort(key=lambda t: t.completed_at or 0)
            for old in completed[:len(completed) - self._max_tasks // 2]:
                del self._tasks[old.task_id]

        return task

    def update_task(self, task_id: str, **kwargs):
        task = self._tasks.get(task_id)
        if task:
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[str] = None,
        assigned_agent: Optional[str] = None,
        assigned_manager: Optional[str] = None,
        limit: int = 100,
    ) -> List[Task]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        if assigned_agent:
            tasks = [t for t in tasks if t.assigned_agent == assigned_agent]
        if assigned_manager:
            tasks = [t for t in tasks if t.assigned_manager == assigned_manager]
        tasks.sort(key=lambda t: (t.priority.value, t.created_at), reverse=True)
        return tasks[:limit]

    def get_next_ready(self) -> Optional[Task]:
        ready = [
            t for t in self._tasks.values()
            if t.status == TaskStatus.PENDING
            and t.task_id not in self._running
        ]
        if not ready:
            return None
        for task in ready:
            if all(
                dep in self._tasks and self._tasks[dep].status == TaskStatus.COMPLETED
                for dep in task.dependencies
            ):
                return task
        return None

    async def execute_task(self, task_id: str) -> Any:
        task = self._tasks.get(task_id)
        if not task:
            return None

        handler = self._handlers.get(task.task_type)
        if not handler:
            task.status = TaskStatus.FAILED
            task.error = f"No handler registered for task type '{task.task_type}'"
            return None

        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        task.add_log("INFO", f"Task started (attempt {task.retry_count + 1}/{task.max_retries + 1})")

        try:
            if task.timeout_seconds:
                result = await asyncio.wait_for(handler(task), timeout=task.timeout_seconds)
            else:
                result = await handler(task)

            task.result = result
            task.status = TaskStatus.COMPLETED
            task.progress = 1.0
            task.completed_at = time.time()
            task.execution_time = task.completed_at - task.started_at
            task.confidence_score = min(1.0, task.confidence_score + 0.3)
            task.add_log("INFO", f"Task completed in {task.execution_time:.2f}s")
            return result

        except asyncio.TimeoutError:
            task.add_log("ERROR", f"Task timed out after {task.timeout_seconds}s")
            return await self._handle_retry(task)
        except Exception as e:
            task.add_log("ERROR", f"Task failed: {str(e)}")
            return await self._handle_retry(task)

    async def _handle_retry(self, task: Task) -> Optional[Any]:
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = TaskStatus.RETRYING
            wait = 2 ** task.retry_count
            task.add_log("INFO", f"Retrying in {wait}s (attempt {task.retry_count}/{task.max_retries})")
            await asyncio.sleep(wait)
            return await self.execute_task(task.task_id)
        else:
            task.status = TaskStatus.FAILED
            task.completed_at = time.time()
            task.execution_time = task.completed_at - (task.started_at or task.completed_at)
            task.confidence_score = 0.0
            task.add_log("ERROR", f"Task failed after {task.max_retries} retries")
            return None

    def cancel_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task and task.status in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.BLOCKED):
            task.status = TaskStatus.CANCELLED
            task.completed_at = time.time()
            task.add_log("WARNING", "Task cancelled")
            if task_id in self._running:
                self._running[task_id].cancel()
                del self._running[task_id]
            return True
        return False

    def resolve_dependencies(self, task_id: str):
        completed = self._tasks.get(task_id)
        if not completed or completed.status != TaskStatus.COMPLETED:
            return
        for task in self._tasks.values():
            if task.status == TaskStatus.BLOCKED and task_id in task.dependencies:
                if all(
                    dep in self._tasks and self._tasks[dep].status == TaskStatus.COMPLETED
                    for dep in task.dependencies
                ):
                    task.status = TaskStatus.PENDING
                    task.add_log("INFO", "Dependencies met, task unblocked")

    def get_stats(self) -> Dict[str, Any]:
        statuses = {}
        for t in self._tasks.values():
            s = t.status.value
            statuses[s] = statuses.get(s, 0) + 1
        return {
            "total": len(self._tasks),
            "running": len(self._running),
            "statuses": statuses,
            "max_concurrent": self._max_concurrent,
        }


task_orchestrator = TaskOrchestrator()