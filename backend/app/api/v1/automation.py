"""
Zentar Intelligence — Automation API Routes

Endpoints for managing automation workflows.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.automation.actions import (
    create_ai_action,
    create_delay_action,
    create_http_action,
    create_notification_action,
)
from app.automation.engine import AutomationAction, AutomationTrigger, AutomationWorkflow, automation_engine
from app.automation.triggers import (
    create_app_trigger,
    create_notification_trigger,
    create_schedule_trigger,
    create_time_trigger,
)
from app.core.security import get_current_user

logger = logging.getLogger("zentar.api.automation")
router = APIRouter(prefix="/automation", tags=["automation"])


# ──────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────

class TriggerConfig(BaseModel):
    trigger_type: str  # schedule, app_event, notification, time, webhook
    config: Dict[str, Any]


class ActionConfig(BaseModel):
    action_type: str  # http_request, notification, delay, ai_prompt, condition
    config: Dict[str, Any]


class CreateWorkflowRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    triggers: List[TriggerConfig] = []
    actions: List[ActionConfig] = []
    enabled: bool = True


class UpdateWorkflowRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    triggers: Optional[List[TriggerConfig]] = None
    actions: Optional[List[ActionConfig]] = None
    enabled: Optional[bool] = None


# ──────────────────────────────────────────
# Routes
# ──────────────────────────────────────────

@router.get("")
async def list_workflows(
    enabled_only: bool = False,
    user_id: str = Depends(get_current_user),
):
    """List all automation workflows."""
    workflows = automation_engine.list_workflows(enabled_only=enabled_only)
    return {
        "success": True,
        "data": {
            "workflows": [w.to_dict() for w in workflows],
            "total": len(workflows),
        },
    }


@router.post("")
async def create_workflow(
    request: CreateWorkflowRequest,
    user_id: str = Depends(get_current_user),
):
    """Create a new automation workflow."""
    import uuid
    workflow = AutomationWorkflow(
        workflow_id=str(uuid.uuid4()),
        name=request.name,
        description=request.description,
        enabled=request.enabled,
    )

    for t in request.triggers:
        trigger = _build_trigger(t.trigger_type, t.config)
        workflow.add_trigger(trigger)

    for a in request.actions:
        action = _build_action(a.action_type, a.config)
        workflow.add_action(action)

    automation_engine.register_workflow(workflow)
    return {"success": True, "data": workflow.to_dict()}


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    user_id: str = Depends(get_current_user),
):
    """Get workflow details."""
    workflow = automation_engine.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"success": True, "data": workflow.to_dict()}


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    request: UpdateWorkflowRequest,
    user_id: str = Depends(get_current_user),
):
    """Update a workflow."""
    workflow = automation_engine.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if request.name is not None:
        workflow.name = request.name
    if request.description is not None:
        workflow.description = request.description
    if request.enabled is not None:
        workflow.enabled = request.enabled
    if request.triggers is not None:
        workflow.triggers = [_build_trigger(t.trigger_type, t.config) for t in request.triggers]
    if request.actions is not None:
        workflow.actions = [_build_action(a.action_type, a.config) for a in request.actions]

    return {"success": True, "data": workflow.to_dict()}


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    user_id: str = Depends(get_current_user),
):
    """Delete a workflow."""
    workflow = automation_engine.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    automation_engine.delete_workflow(workflow_id)
    return {"success": True, "message": "Workflow deleted"}


@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    user_id: str = Depends(get_current_user),
):
    """Execute a workflow immediately."""
    results = await automation_engine.execute_workflow(workflow_id)
    return {"success": True, "data": {"results": results}}


@router.get("/stats")
async def automation_stats(
    user_id: str = Depends(get_current_user),
):
    """Get automation engine statistics."""
    return {"success": True, "data": automation_engine.get_stats()}


# ──────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────

def _build_trigger(trigger_type: str, config: Dict[str, Any]) -> AutomationTrigger:
    """Build a trigger from type and config."""
    builders = {
        "schedule": lambda c: create_schedule_trigger(c.get("cron", "every_3600")),
        "app_event": lambda c: create_app_trigger(c["app_package"], c.get("event", "opened")),
        "notification": lambda c: create_notification_trigger(
            c.get("app_package"), c.get("keyword")
        ),
        "time": lambda c: create_time_trigger(c["hour"], c["minute"], c.get("days")),
        "webhook": lambda c: create_webhook_trigger(c.get("path", "/hook"), c.get("method", "POST")),
    }
    builder = builders.get(trigger_type)
    if not builder:
        raise HTTPException(status_code=400, detail=f"Unknown trigger type: {trigger_type}")
    return builder(config)


def _build_action(action_type: str, config: Dict[str, Any]) -> AutomationAction:
    """Build an action from type and config."""
    builders = {
        "http_request": lambda c: create_http_action(c["url"], c.get("method", "GET"), c.get("headers"), c.get("body")),
        "notification": lambda c: create_notification_action(c["title"], c["content"]),
        "delay": lambda c: create_delay_action(c["seconds"]),
        "ai_prompt": lambda c: create_ai_action(c["prompt"], c.get("provider")),
    }
    builder = builders.get(action_type)
    if not builder:
        raise HTTPException(status_code=400, detail=f"Unknown action type: {action_type}")
    return builder(config)
