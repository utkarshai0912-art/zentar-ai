"""
Zentar Intelligence — Workflow Builder

Allows users to visually create workflows using agents with support for
conditions, loops, schedules, triggers, webhooks, and reusable templates.
"""

import asyncio
import json
import logging
import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Callable

logger = logging.getLogger("zentar.agents.workflow")


class WorkflowNodeType(Enum):
    TASK = "task"
    CONDITION = "condition"
    LOOP = "loop"
    TRIGGER = "trigger"
    WEBHOOK = "webhook"
    DELAY = "delay"
    AI_ACTION = "ai_action"
    NOTIFICATION = "notification"


class WorkflowConnection:
    """Connection between workflow nodes."""

    def __init__(self, source_id: str, target_id: str, label: Optional[str] = None):
        self.source_id = source_id
        self.target_id = target_id
        self.label = label or "default"


class WorkflowNode:
    """A node in a workflow graph."""

    def __init__(
        self,
        node_id: str,
        node_type: WorkflowNodeType,
        config: Dict[str, Any],
        position: Optional[Dict[str, int]] = None,
    ):
        self.node_id = node_id
        self.node_type = node_type
        self.config = config
        self.position = position or {"x": 0, "y": 0}
        self.label: str = config.get("label", node_type.value)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "config": self.config,
            "position": self.position,
            "label": self.label,
        }


class WorkflowDefinition:
    """Complete workflow definition."""

    def __init__(self, workflow_id: str, name: str, description: Optional[str] = None):
        self.workflow_id = workflow_id
        self.name = name
        self.description = description or ""
        self.nodes: Dict[str, WorkflowNode] = {}
        self.connections: List[WorkflowConnection] = []
        self.is_active = False
        self.is_template = False
        self.category: Optional[str] = None
        self.tags: List[str] = []
        self.created_at = time.time()
        self.updated_at = time.time()
        self.execution_count = 0
        self.last_executed_at: Optional[float] = None

    def add_node(self, node: WorkflowNode):
        self.nodes[node.node_id] = node

    def add_connection(self, connection: WorkflowConnection):
        self.connections.append(connection)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "connections": [
                {"source_id": c.source_id, "target_id": c.target_id, "label": c.label}
                for c in self.connections
            ],
            "is_active": self.is_active,
            "is_template": self.is_template,
            "category": self.category,
            "tags": self.tags,
            "execution_count": self.execution_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class WorkflowExecutor:
    """Executes a workflow by traversing its graph."""

    def __init__(self):
        self._results: Dict[str, Any] = {}

    async def execute(
        self,
        workflow: WorkflowDefinition,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        inputs = inputs or {}
        log: List[Dict[str, Any]] = []
        self._results = dict(inputs)

        # Find start nodes (no incoming connections)
        targets = {c.target_id for c in workflow.connections}
        start_nodes = [n for n_id, n in workflow.nodes.items() if n_id not in targets]

        # Execute in topological order
        executed = set()
        queue = list(start_nodes)

        while queue:
            node = queue.pop(0)
            if node.node_id in executed:
                continue

            # Check if all dependencies are met
            deps = [
                c.source_id for c in workflow.connections
                if c.target_id == node.node_id
            ]
            if not all(d in executed for d in deps):
                continue

            try:
                result = await self._execute_node(node, self._results)
                self._results[node.node_id] = result
                executed.add(node.node_id)
                log.append({
                    "node_id": node.node_id,
                    "node_type": node.node_type.value,
                    "status": "completed",
                    "result": str(result)[:200],
                })
            except Exception as e:
                log.append({
                    "node_id": node.node_id,
                    "node_type": node.node_type.value,
                    "status": "failed",
                    "error": str(e),
                })

            # Add next nodes
            for conn in workflow.connections:
                if conn.source_id == node.node_id:
                    next_node = workflow.nodes.get(conn.target_id)
                    if next_node and next_node.node_id not in executed:
                        queue.append(next_node)

        workflow.execution_count += 1
        workflow.last_executed_at = time.time()

        return {
            "workflow_id": workflow.workflow_id,
            "status": "completed",
            "execution_log": log,
            "results": {k: str(v)[:200] for k, v in self._results.items()},
        }

    async def _execute_node(self, node: WorkflowNode, context: Dict[str, Any]) -> Any:
        if node.node_type == WorkflowNodeType.TASK:
            return await self._execute_task(node, context)
        elif node.node_type == WorkflowNodeType.CONDITION:
            return self._evaluate_condition(node, context)
        elif node.node_type == WorkflowNodeType.LOOP:
            return await self._execute_loop(node, context)
        elif node.node_type == WorkflowNodeType.DELAY:
            return await self._execute_delay(node)
        elif node.node_type == WorkflowNodeType.AI_ACTION:
            return await self._execute_ai_action(node, context)
        elif node.node_type == WorkflowNodeType.NOTIFICATION:
            return self._execute_notification(node, context)
        return None

    async def _execute_task(self, node: WorkflowNode, context: Dict[str, Any]) -> str:
        task_type = node.config.get("task_type", "default")
        params = node.config.get("params", {})
        return f"Executed task '{task_type}' with params: {params}"

    def _evaluate_condition(self, node: WorkflowNode, context: Dict[str, Any]) -> bool:
        field = node.config.get("field", "")
        operator = node.config.get("operator", "equals")
        value = node.config.get("value", "")
        actual = context.get(field)
        if operator == "equals":
            return actual == value
        elif operator == "greater_than":
            return float(actual or 0) > float(value)
        elif operator == "less_than":
            return float(actual or 0) < float(value)
        elif operator == "contains":
            return value in str(actual or "")
        return True

    async def _execute_loop(self, node: WorkflowNode, context: Dict[str, Any]) -> List[Any]:
        iterations = node.config.get("iterations", 1)
        results = []
        for i in range(iterations):
            results.append(f"Iteration {i + 1}")
            await asyncio.sleep(0.1)
        return results

    async def _execute_delay(self, node: WorkflowNode) -> str:
        seconds = node.config.get("seconds", 1)
        await asyncio.sleep(seconds)
        return f"Delayed {seconds}s"

    async def _execute_ai_action(self, node: WorkflowNode, context: Dict[str, Any]) -> str:
        from app.services.ai_service import provider_registry
        prompt = node.config.get("prompt", "")
        formatted = prompt
        for key, value in context.items():
            formatted = formatted.replace(f"{{{{{key}}}}}", str(value))
        result = ""
        async for event in provider_registry.route_request(
            messages=[{"role": "user", "content": formatted}],
            temperature=0.5,
            stream=False,
        ):
            if event["type"] == "done":
                result = event.get("content", "")
        return result

    def _execute_notification(self, node: WorkflowNode, context: Dict[str, Any]) -> str:
        message = node.config.get("message", "")
        return f"Notification: {message}"


class WorkflowBuilder:
    """Builds and manages workflow definitions."""

    def __init__(self):
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._templates: Dict[str, WorkflowDefinition] = {}
        self.executor = WorkflowExecutor()

    def create_workflow(self, name: str, description: Optional[str] = None) -> WorkflowDefinition:
        wf = WorkflowDefinition(
            workflow_id=str(uuid.uuid4()),
            name=name,
            description=description,
        )
        self._workflows[wf.workflow_id] = wf
        return wf

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        return self._workflows.get(workflow_id)

    def update_workflow(self, workflow_id: str, **kwargs) -> Optional[WorkflowDefinition]:
        wf = self._workflows.get(workflow_id)
        if not wf:
            return None
        for key, value in kwargs.items():
            if hasattr(wf, key):
                setattr(wf, key, value)
        wf.updated_at = time.time()
        return wf

    def delete_workflow(self, workflow_id: str) -> bool:
        return self._workflows.pop(workflow_id, None) is not None

    def save_as_template(self, workflow_id: str, category: Optional[str] = None) -> Optional[WorkflowDefinition]:
        wf = self._workflows.get(workflow_id)
        if not wf:
            return None
        import copy
        template = copy.deepcopy(wf)
        template.workflow_id = str(uuid.uuid4())
        template.is_template = True
        template.is_active = False
        template.category = category or wf.category
        template.execution_count = 0
        self._templates[template.workflow_id] = template
        return template

    def list_workflows(self, is_template: bool = False) -> List[Dict[str, Any]]:
        source = self._templates if is_template else self._workflows
        return [wf.to_dict() for wf in source.values()]

    async def execute_workflow(self, workflow_id: str, inputs: Optional[Dict] = None) -> Dict[str, Any]:
        wf = self._workflows.get(workflow_id)
        if not wf:
            raise ValueError(f"Workflow not found: {workflow_id}")
        return await self.executor.execute(wf, inputs)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_workflows": len(self._workflows),
            "total_templates": len(self._templates),
            "total_executions": sum(w.execution_count for w in self._workflows.values()),
        }


workflow_builder = WorkflowBuilder()