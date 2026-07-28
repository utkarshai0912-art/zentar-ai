"""
Zentar Intelligence — CEO & Multi-Agent API Routes
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.agents.ceo_agent import ceo_manager, CEOAgent
from app.agents.manager_agents import list_managers
from app.agents.worker_agents import list_workers
from app.agents.sales_team import SalesPipeline, sales_pipeline_manager
from app.agents.custom_agent_builder import custom_agent_builder
from app.agents.workflow_builder import workflow_builder
from app.agents.task_system import task_orchestrator, TaskPriority
from app.agents.agent_memory import agent_memory_manager
from app.services.browser_service import browser_service
from app.core.security import get_current_user
from app.schemas import APIResponse

logger = logging.getLogger("zentar.api.agents")
router = APIRouter(prefix="/ceo", tags=["CEO Agent"])


@router.post("/execute")
async def ceo_execute(objective: str, current_user=Depends(get_current_user)):
    session = ceo_manager.create_session()
    return APIResponse(data={"session_id": session.session_id, "status": "started"})


@router.get("/sessions")
async def list_sessions(current_user=Depends(get_current_user)):
    return APIResponse(data=ceo_manager.list_sessions())


@router.get("/managers")
async def get_managers(current_user=Depends(get_current_user)):
    return APIResponse(data=list_managers())


@router.get("/workers")
async def get_workers(current_user=Depends(get_current_user)):
    return APIResponse(data=list_workers())


# ── Sales Pipeline ──

sales_router = APIRouter(prefix="/sales", tags=["Sales"])


@sales_router.post("/pipeline")
async def start_sales_pipeline(target_market: str, current_user=Depends(get_current_user)):
    pipeline = sales_pipeline_manager.create_pipeline()
    return APIResponse(data={"pipeline_id": pipeline.pipeline_id, "target_market": target_market, "status": "created"})


@sales_router.get("/pipelines")
async def list_pipelines(current_user=Depends(get_current_user)):
    return APIResponse(data=sales_pipeline_manager.list_pipelines())


# ── Custom Agents ──

custom_router = APIRouter(prefix="/custom-agents", tags=["Custom Agents"])


@custom_router.post("")
async def create_custom_agent(name: str, role: str, system_prompt: str, avatar: str = None,
                              model: str = None, provider: str = None, temperature: float = 0.7,
                              current_user=Depends(get_current_user)):
    agent = custom_agent_builder.create_agent(
        name=name, role=role, system_prompt=system_prompt,
        avatar=avatar, model=model, provider=provider, temperature=temperature,
    )
    return APIResponse(data=agent.to_dict())


@custom_router.get("")
async def list_custom_agents(current_user=Depends(get_current_user)):
    return APIResponse(data=custom_agent_builder.list_agents())


@custom_router.post("/{agent_id}/activate")
async def activate_custom_agent(agent_id: str, current_user=Depends(get_current_user)):
    ok = custom_agent_builder.activate_agent(agent_id)
    if not ok:
        raise HTTPException(404, "Agent not found")
    return APIResponse(message="Agent activated")


@custom_router.post("/{agent_id}/deactivate")
async def deactivate_custom_agent(agent_id: str, current_user=Depends(get_current_user)):
    ok = custom_agent_builder.deactivate_agent(agent_id)
    if not ok:
        raise HTTPException(404, "Agent not found")
    return APIResponse(message="Agent deactivated")


@custom_router.delete("/{agent_id}")
async def delete_custom_agent(agent_id: str, current_user=Depends(get_current_user)):
    ok = custom_agent_builder.delete_agent(agent_id)
    if not ok:
        raise HTTPException(404, "Agent not found")
    return APIResponse(message="Agent deleted")


# ── Workflow Builder ──

workflow_router = APIRouter(prefix="/workflows", tags=["Workflows"])


@workflow_router.post("")
async def create_workflow(name: str, description: str = None, current_user=Depends(get_current_user)):
    wf = workflow_builder.create_workflow(name, description)
    return APIResponse(data=wf.to_dict())


@workflow_router.get("")
async def list_workflows(current_user=Depends(get_current_user)):
    return APIResponse(data=workflow_builder.list_workflows())


@workflow_router.post("/{workflow_id}/execute")
async def execute_workflow(workflow_id: str, current_user=Depends(get_current_user)):
    try:
        result = await workflow_builder.execute_workflow(workflow_id)
        return APIResponse(data=result)
    except ValueError as e:
        raise HTTPException(404, str(e))


@workflow_router.post("/{workflow_id}/nodes")
async def add_workflow_node(workflow_id: str, payload: dict, current_user=Depends(get_current_user)):
    from app.agents.workflow_builder import WorkflowNode, WorkflowNodeType
    wf = workflow_builder.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")
    node = WorkflowNode(
        node_id=payload.get("node_id", str(uuid.uuid4())),
        node_type=WorkflowNodeType(payload["node_type"]),
        config=payload.get("config", {}),
        position=payload.get("position"),
    )
    wf.add_node(node)
    return APIResponse(data=node.to_dict())


@workflow_router.post("/{workflow_id}/connections")
async def add_workflow_connection(workflow_id: str, payload: dict, current_user=Depends(get_current_user)):
    from app.agents.workflow_builder import WorkflowConnection
    wf = workflow_builder.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")
    conn = WorkflowConnection(
        source_id=payload["source_id"],
        target_id=payload["target_id"],
        label=payload.get("label"),
    )
    wf.add_connection(conn)
    return APIResponse(message="Connection added")


@workflow_router.post("/{workflow_id}/save-template")
async def save_workflow_template(workflow_id: str, category: str = None, current_user=Depends(get_current_user)):
    template = workflow_builder.save_as_template(workflow_id, category)
    if not template:
        raise HTTPException(404, "Workflow not found")
    return APIResponse(data=template.to_dict())


@workflow_router.get("/templates")
async def list_templates(current_user=Depends(get_current_user)):
    return APIResponse(data=workflow_builder.list_workflows(is_template=True))


# ── Task System ──

task_router = APIRouter(prefix="/tasks", tags=["Tasks"])


@task_router.get("")
async def list_tasks(status: str = None, task_type: str = None, limit: int = 50,
                     current_user=Depends(get_current_user)):
    tasks = task_orchestrator.list_tasks(limit=limit)
    return APIResponse(data=[t.to_dict() for t in tasks])


@task_router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, current_user=Depends(get_current_user)):
    ok = task_orchestrator.cancel_task(task_id)
    if not ok:
        raise HTTPException(404, "Task not found")
    return APIResponse(message="Task cancelled")


# ── Browser Service ──

browser_router = APIRouter(prefix="/browser", tags=["Browser"])


@browser_router.get("/status")
async def browser_status(current_user=Depends(get_current_user)):
    return APIResponse(data=browser_service.get_stats())


@browser_router.post("/context")
async def create_browser_context(current_user=Depends(get_current_user)):
    try:
        ctx_id = await browser_service.new_context()
        return APIResponse(data={"context_id": ctx_id})
    except Exception as e:
        raise HTTPException(503, f"Browser not available: {e}")


@browser_router.post("/navigate")
async def browser_navigate(url: str, context_id: str = None, current_user=Depends(get_current_user)):
    try:
        tab_id = await browser_service.new_tab(url, context_id)
        title = await browser_service.get_title(tab_id)
        return APIResponse(data={"tab_id": tab_id, "title": title, "url": url})
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Memory Stats ──

@router.get("/memory-stats")
async def memory_stats(current_user=Depends(get_current_user)):
    return APIResponse(data=agent_memory_manager.get_stats())