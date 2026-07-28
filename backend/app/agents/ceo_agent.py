"""
Zentar Intelligence — CEO Agent

Top-level orchestrator that breaks objectives into tasks,
assigns work to Manager Agents, monitors execution,
and combines results into a final response.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, AsyncGenerator

from app.services.ai_service import provider_registry

logger = logging.getLogger("zentar.agents.ceo")


class CEOSubTask:
    """A sub-task managed by the CEO agent."""
    
    def __init__(
        self,
        task_id: str,
        description: str,
        assigned_manager: str,
        depends_on: Optional[List[str]] = None,
        priority: int = 5,
    ):
        self.task_id = task_id
        self.description = description
        self.assigned_manager = assigned_manager
        self.depends_on = depends_on or []
        self.priority = priority
        self.status = "pending"  # pending, running, completed, failed
        self.result: Optional[Any] = None
        self.error: Optional[str] = None
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.confidence: float = 0.0


class CEOAgent:
    """
    CEO Agent — top-level orchestrator.
    
    Breaks user objectives into tasks, assigns them to managers,
    monitors execution, retries failures, and combines outputs.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.sub_tasks: Dict[str, CEOSubTask] = {}
        self._provider: Optional[str] = None
        self._model: Optional[str] = None
    
    def configure(self, provider: Optional[str] = None, model: Optional[str] = None):
        self._provider = provider
        self._model = model
    
    async def execute(
        self,
        objective: str,
        context: Optional[Dict[str, Any]] = None,
        stream: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Execute a user objective through the agent hierarchy.
        
        Yields events: planning, task_start, task_progress, task_complete, 
                       chunk, done, error
        """
        yield {"type": "planning", "content": f"Analyzing objective: {objective}"}
        
        # Step 1: Break down the objective into sub-tasks
        tasks = await self._break_down_objective(objective, context or {})
        
        yield {
            "type": "planning",
            "content": f"Broken down into {len(tasks)} tasks",
            "tasks": [t.description for t in tasks],
        }
        
        # Step 2: Execute tasks respecting dependencies
        results = {}
        async for event in self._execute_tasks_stream(tasks, stream):
            if event["type"] in ("task_start", "task_complete", "task_failed"):
                yield event
            else:
                # Collect task results
                task_id = event.get("task_id")
                if task_id:
                    results[task_id] = event.get("result")
        
        # Step 3: Combine all results into final response
        if stream:
            async for event in self._synthesize_response(objective, results):
                yield event
        else:
            final = await self._synthesize_response_async(objective, results)
            yield {"type": "done", "content": final}
    
    async def _break_down_objective(
        self,
        objective: str,
        context: Dict[str, Any],
    ) -> List[CEOSubTask]:
        """Use AI to break down the objective into manager-assigned tasks."""
        prompt = (
            "You are the CEO Agent of an enterprise AI system. "
            "Break down the following user objective into specific tasks "
            "that can be assigned to specialized Manager Agents.\n\n"
            f"Objective: {objective}\n\n"
            f"Available Manager Agents:\n"
            "- Engineering Manager: coding, development, technical tasks\n"
            "- Research Manager: information gathering, analysis, web research\n"
            "- Automation Manager: workflow automation, scheduling, triggers\n"
            "- Marketing Manager: content creation, marketing strategy\n"
            "- Sales Manager: lead generation, sales outreach\n"
            "- Security Manager: security review, vulnerability assessment\n"
            "- Content Manager: writing, editing, documentation\n"
            "- Customer Support Manager: user support, issue resolution\n\n"
            "Respond with a JSON array of tasks. Each task must have:\n"
            "- task_id: unique string\n"
            "- description: clear task description\n"
            "- assigned_manager: one of the manager names above\n"
            "- depends_on: array of task_ids this depends on (empty if none)\n"
            "- priority: 1-10 (10 = highest)\n\n"
            "Return ONLY the JSON array, no other text."
        )
        
        tasks = []
        try:
            async for event in provider_registry.route_request(
                messages=[{"role": "user", "content": prompt}],
                provider_name=self._provider,
                model=self._model,
                temperature=0.3,
                max_tokens=4096,
                stream=False,
            ):
                if event["type"] == "done":
                    content = event.get("content", "")
                    # Extract JSON array from response
                    content = content.strip()
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0]
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0]
                    try:
                        task_data = json.loads(content)
                        if isinstance(task_data, list):
                            for td in task_data:
                                tasks.append(CEOSubTask(
                                    task_id=td.get("task_id", str(uuid.uuid4())),
                                    description=td.get("description", ""),
                                    assigned_manager=td.get("assigned_manager", "Research Manager"),
                                    depends_on=td.get("depends_on", []),
                                    priority=td.get("priority", 5),
                                ))
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse CEO task breakdown: %s", content[:200])
        except Exception as e:
            logger.error("CEO breakdown failed: %s", e)
        
        # Fallback: create a single generic task
        if not tasks:
            tasks.append(CEOSubTask(
                task_id=str(uuid.uuid4()),
                description=objective,
                assigned_manager="Research Manager",
                priority=5,
            ))
        
        for t in tasks:
            self.sub_tasks[t.task_id] = t
        
        return tasks
    
    async def _execute_tasks_stream(
        self,
        tasks: List[CEOSubTask],
        stream: bool,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute tasks respecting dependency ordering."""
        results = {}
        completed = set()
        pending = list(tasks)
        
        while pending:
            # Find tasks whose dependencies are met
            ready = [
                t for t in pending
                if all(dep in completed for dep in t.depends_on)
            ]
            
            if not ready:
                # Circular dependency — break it
                logger.warning("Circular dependency detected, forcing execution")
                ready = [pending[0]]
            
            # Execute ready tasks in parallel
            batch = []
            for task in ready:
                pending.remove(task)
                task.status = "running"
                task.started_at = time.time()
                if stream:
                    yield {
                        "type": "task_start",
                        "task_id": task.task_id,
                        "description": task.description,
                        "assigned_manager": task.assigned_manager,
                    }
                batch.append(self._run_task(task))
            
            # Wait for all to complete
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            
            for task, result in zip(ready, batch_results):
                if isinstance(result, Exception):
                    task.status = "failed"
                    task.error = str(result)
                    task.confidence = 0.0
                    logger.error("Task %s failed: %s", task.task_id, result)
                else:
                    task.status = "completed"
                    task.result = result
                    task.completed_at = time.time()
                    task.confidence = 0.8
                    completed.add(task.task_id)
                    results[task.task_id] = result
                
                if stream:
                    yield {
                        "type": "task_complete" if task.status == "completed" else "task_failed",
                        "task_id": task.task_id,
                        "description": task.description,
                        "result": task.result if task.status == "completed" else None,
                        "error": task.error if task.status == "failed" else None,
                        "execution_time": (task.completed_at or time.time()) - (task.started_at or time.time()),
                    }
        
        return
    
    async def _run_task(self, task: CEOSubTask) -> Any:
        """Route a task to the appropriate manager agent."""
        try:
            from app.agents.manager_agents import get_manager
            manager = get_manager(task.assigned_manager)
            if manager:
                result = await manager.execute(task.description)
                return result
        except Exception as e:
            logger.warning("Manager agent error: %s", e)
        
        # Fallback: use AI directly
        prompt = f"Complete the following task:\n\n{task.description}"
        result = ""
        try:
            async for event in provider_registry.route_request(
                messages=[{"role": "user", "content": prompt}],
                provider_name=self._provider,
                model=self._model,
                temperature=0.5,
                max_tokens=4096,
                stream=False,
            ):
                if event["type"] == "done":
                    result = event.get("content", "")
        except Exception as e:
            raise Exception(f"Task execution failed: {e}")
        
        return result
    
    async def _synthesize_response(
        self,
        objective: str,
        results: Dict[str, Any],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Synthesize all task results into a final response."""
        results_text = json.dumps(results, indent=2)
        prompt = (
            "You are the CEO Agent. Synthesize the following task results "
            "into a comprehensive final response for the user.\n\n"
            f"Original objective: {objective}\n\n"
            f"Task results:\n{results_text}\n\n"
            "Provide a well-structured response that addresses the user's objective."
        )
        
        async for event in provider_registry.route_request(
            messages=[{"role": "user", "content": prompt}],
            provider_name=self._provider,
            model=self._model,
            temperature=0.5,
            stream=True,
        ):
            yield event
    
    async def _synthesize_response_async(self, objective: str, results: Dict[str, Any]) -> str:
        """Non-streaming version of response synthesis."""
        results_text = json.dumps(results, indent=2)
        prompt = (
            "You are the CEO Agent. Synthesize the following task results "
            "into a comprehensive final response for the user.\n\n"
            f"Original objective: {objective}\n\n"
            f"Task results:\n{results_text}\n\n"
            "Provide a well-structured response."
        )
        
        async for event in provider_registry.route_request(
            messages=[{"role": "user", "content": prompt}],
            provider_name=self._provider,
            model=self._model,
            temperature=0.5,
            stream=False,
        ):
            if event["type"] == "done":
                return event.get("content", "")
        return "Unable to synthesize response."


class CEOAgentManager:
    """Manages CEO Agent sessions."""
    
    def __init__(self):
        self._sessions: Dict[str, CEOAgent] = {}
    
    def create_session(self, session_id: Optional[str] = None) -> CEOAgent:
        sid = session_id or str(uuid.uuid4())
        agent = CEOAgent(session_id=sid)
        self._sessions[sid] = agent
        return agent
    
    def get_session(self, session_id: str) -> Optional[CEOAgent]:
        return self._sessions.get(session_id)
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        return [
            {"session_id": sid, "tasks": len(agent.sub_tasks)}
            for sid, agent in self._sessions.items()
        ]


# Global CEO manager
ceo_manager = CEOAgentManager()
