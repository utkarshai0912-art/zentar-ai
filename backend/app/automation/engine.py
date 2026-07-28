"""
Zentar Intelligence — Automation Engine

Workflow-based automation engine with triggers, conditions, and actions.
Enables no-code automation of Android device tasks.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from app.core.config import get_settings

logger = logging.getLogger("zentar.automation")

settings = get_settings()


class AutomationTrigger:
    """A trigger that initiates an automation workflow."""

    def __init__(
        self,
        trigger_id: str,
        trigger_type: str,
        config: Dict[str, Any],
    ):
        self.trigger_id = trigger_id
        self.trigger_type = trigger_type  # event, schedule, webhook, notification
        self.config = config
        self._condition: Optional[Callable] = None

    def set_condition(self, condition: Callable[[], bool]):
        """Set a condition function that must be met for the trigger to fire."""
        self._condition = condition

    def should_fire(self, context: Optional[Dict] = None) -> bool:
        """Check if trigger condition is met."""
        if self._condition:
            return self._condition()
        return True


class AutomationAction:
    """An action to execute as part of an automation workflow."""

    def __init__(
        self,
        action_id: str,
        action_type: str,
        config: Dict[str, Any],
        handler: Optional[Callable] = None,
    ):
        self.action_id = action_id
        self.action_type = action_type
        self.config = config
        self.handler = handler

    async def execute(self, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute the action."""
        if not self.handler:
            return {"success": False, "error": "No handler configured"}
        try:
            result = await self.handler(**(context or {}))
            return {"success": True, "result": result}
        except Exception as e:
            logger.error("Action %s failed: %s", self.action_id, e)
            return {"success": False, "error": str(e)}


class AutomationWorkflow:
    """A complete automation workflow with triggers and actions."""

    def __init__(
        self,
        workflow_id: str,
        name: str,
        description: Optional[str] = None,
        enabled: bool = True,
    ):
        self.workflow_id = workflow_id
        self.name = name
        self.description = description or ""
        self.enabled = enabled
        self.triggers: List[AutomationTrigger] = []
        self.actions: List[AutomationAction] = []
        self.conditions: List[Dict[str, Any]] = []
        self.created_at = time.time()
        self.execution_count = 0
        self.last_execution: Optional[float] = None

    def add_trigger(self, trigger: AutomationTrigger):
        """Add a trigger to the workflow."""
        self.triggers.append(trigger)

    def add_action(self, action: AutomationAction):
        """Add an action to the workflow."""
        self.actions.append(action)

    async def execute(self, context: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Execute all actions in sequence."""
        if not self.enabled:
            return [{"success": False, "error": "Workflow is disabled"}]

        results = []
        for action in self.actions:
            result = await action.execute(context)
            results.append(result)
            if not result["success"]:
                break  # Stop on failure

        self.execution_count += 1
        self.last_execution = time.time()
        return results

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "triggers": [
                {"id": t.trigger_id, "type": t.trigger_type, "config": t.config}
                for t in self.triggers
            ],
            "actions": [
                {"id": a.action_id, "type": a.action_type, "config": a.config}
                for a in self.actions
            ],
            "execution_count": self.execution_count,
            "last_execution": self.last_execution,
            "created_at": self.created_at,
        }


class AutomationEngine:
    """Manages and executes automation workflows."""

    def __init__(self):
        self._workflows: Dict[str, AutomationWorkflow] = {}
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None

    def register_workflow(self, workflow: AutomationWorkflow):
        """Register an automation workflow."""
        self._workflows[workflow.workflow_id] = workflow
        logger.info("Registered workflow: %s", workflow.name)

    def get_workflow(self, workflow_id: str) -> Optional[AutomationWorkflow]:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)

    def delete_workflow(self, workflow_id: str):
        """Delete a workflow."""
        self._workflows.pop(workflow_id, None)

    def list_workflows(self, enabled_only: bool = False) -> List[AutomationWorkflow]:
        """List all workflows."""
        workflows = list(self._workflows.values())
        if enabled_only:
            workflows = [w for w in workflows if w.enabled]
        return workflows

    async def trigger_event(self, event_type: str, context: Optional[Dict] = None):
        """Trigger workflows matching an event type."""
        context = context or {}
        for workflow in self._workflows.values():
            if not workflow.enabled:
                continue
            for trigger in workflow.triggers:
                if trigger.trigger_type == event_type and trigger.should_fire(context):
                    logger.info("Triggering workflow: %s (event: %s)", workflow.name, event_type)
                    asyncio.create_task(workflow.execute(context))

    async def execute_workflow(self, workflow_id: str, context: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Execute a specific workflow by ID."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return [{"success": False, "error": "Workflow not found"}]
        return await workflow.execute(context)

    def get_stats(self) -> Dict[str, Any]:
        """Get automation engine statistics."""
        total = len(self._workflows)
        enabled = sum(1 for w in self._workflows.values() if w.enabled)
        total_executions = sum(w.execution_count for w in self._workflows.values())
        return {
            "total_workflows": total,
            "enabled_workflows": enabled,
            "total_executions": total_executions,
            "is_running": self._running,
        }


# Global automation engine
automation_engine = AutomationEngine()
