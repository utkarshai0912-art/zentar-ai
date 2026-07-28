"""
Zentar Intelligence — Scheduler Worker

Background task scheduler for periodic operations, maintenance,
and automation workflow scheduling.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from app.core.config import get_settings

logger = logging.getLogger("zentar.workers.scheduler")

settings = get_settings()


class ScheduledTask:
    """A task that runs on a schedule."""

    def __init__(
        self,
        task_id: str,
        name: str,
        interval_seconds: int,
        handler: Callable[[], Any],
        run_on_start: bool = False,
        max_runtime: int = 300,
    ):
        self.task_id = task_id
        self.name = name
        self.interval = interval_seconds
        self.handler = handler
        self.run_on_start = run_on_start
        self.max_runtime = max_runtime
        self.last_run: Optional[float] = None
        self.run_count = 0
        self.is_running = False

    async def execute(self):
        """Execute the task handler."""
        if self.is_running:
            logger.warning("Task %s is already running, skipping", self.name)
            return

        self.is_running = True
        try:
            start = asyncio.get_event_loop().time()
            if asyncio.iscoroutinefunction(self.handler):
                result = await self.handler()
            else:
                result = self.handler()
            elapsed = asyncio.get_event_loop().time() - start
            self.run_count += 1
            self.last_run = datetime.now(timezone.utc).timestamp()
            logger.info("Task %s completed in %.2fs (run #%d)", self.name, elapsed, self.run_count)
        except asyncio.TimeoutError:
            logger.error("Task %s timed out after %ds", self.name, self.max_runtime)
        except Exception as e:
            logger.error("Task %s failed: %s", self.name, e, exc_info=True)
        finally:
            self.is_running = False


class Scheduler:
    """Background scheduler that runs tasks at fixed intervals."""

    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._main_loop: Optional[asyncio.Task] = None

    def register(self, task: ScheduledTask):
        """Register a scheduled task."""
        self._tasks[task.task_id] = task
        logger.info("Registered scheduled task: %s (every %ds)", task.name, task.interval)

    def unregister(self, task_id: str):
        """Unregister a task."""
        self._tasks.pop(task_id, None)

    async def start(self):
        """Start the scheduler."""
        if self._running:
            return

        self._running = True
        self._main_loop = asyncio.create_task(self._run_loop())
        logger.info("Scheduler started with %d tasks", len(self._tasks))

    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._main_loop:
            self._main_loop.cancel()
            self._main_loop = None
        logger.info("Scheduler stopped")

    async def _run_loop(self):
        """Main scheduler loop."""
        # Run startup tasks
        for task in self._tasks.values():
            if task.run_on_start:
                asyncio.create_task(task.execute())

        while self._running:
            for task in self._tasks.values():
                if task.last_run is None:
                    continue  # Skip tasks waiting for first interval

                elapsed = asyncio.get_event_loop().time() - task.last_run
                if elapsed >= task.interval:
                    asyncio.create_task(task.execute())

            await asyncio.sleep(1)  # Check every second

    async def execute_now(self, task_id: str):
        """Execute a specific task immediately."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        await task.execute()
        return True

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific task."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        return {
            "task_id": task.task_id,
            "name": task.name,
            "interval": task.interval,
            "last_run": task.last_run,
            "run_count": task.run_count,
            "is_running": task.is_running,
        }

    def get_all_status(self) -> List[Dict[str, Any]]:
        """Get status of all tasks."""
        return [self.get_task_status(tid) for tid in self._tasks]

    @property
    def is_running(self) -> bool:
        return self._running


# Global scheduler
scheduler = Scheduler()


# ──────────────────────────────────────────
# Built-in Scheduled Tasks
# ──────────────────────────────────────────

async def cleanup_expired_sessions():
    """Clean up expired sessions and tokens."""
    from app.mcp.auth import mcp_auth_provider
    mcp_auth_provider.cleanup_expired()
    logger.debug("Cleaned up expired MCP tokens")


async def cleanup_old_memories():
    """Periodic memory maintenance."""
    from app.agents.memory_manager import memory_manager
    memory_manager.cleanup_inactive(max_age_minutes=120)
    logger.debug("Cleaned up inactive memory sessions")


async def health_check_task():
    """Periodic health check and logging."""
    logger.debug("Scheduler health check OK")


def register_default_tasks():
    """Register the default scheduled tasks."""
    scheduler.register(ScheduledTask(
        task_id="cleanup_sessions",
        name="Session Cleanup",
        interval_seconds=3600,
        handler=cleanup_expired_sessions,
        run_on_start=False,
    ))
    scheduler.register(ScheduledTask(
        task_id="cleanup_memories",
        name="Memory Cleanup",
        interval_seconds=1800,
        handler=cleanup_old_memories,
        run_on_start=False,
    ))
    scheduler.register(ScheduledTask(
        task_id="health_check",
        name="Health Check",
        interval_seconds=300,
        handler=health_check_task,
        run_on_start=True,
    ))
