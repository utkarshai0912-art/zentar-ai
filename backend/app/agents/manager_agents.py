"""
Zentar Intelligence — Manager Agents

Specialized Manager Agents that delegate to worker agents.
Each manager handles a specific domain.
"""

import asyncio
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from app.services.ai_service import provider_registry

logger = logging.getLogger("zentar.agents.managers")


class ManagerAgent:
    """Base class for all Manager Agents."""
    
    def __init__(self, name: str, role_description: str, system_prompt: str):
        self.name = name
        self.role_description = role_description
        self.system_prompt = system_prompt
        self._provider: Optional[str] = None
        self._model: Optional[str] = None
    
    def configure(self, provider: Optional[str] = None, model: Optional[str] = None):
        self._provider = provider
        self._model = model
    
    async def execute(self, task_description: str) -> str:
        """Execute a task by delegating to workers or handling directly."""
        # Try worker agents first
        worker_result = await self._delegate_to_workers(task_description)
        if worker_result:
            return worker_result
        
        # Fallback: handle directly with AI
        return await self._handle_directly(task_description)
    
    async def _delegate_to_workers(self, task: str) -> Optional[str]:
        """Try to delegate to specialized worker agents."""
        try:
            from app.agents.worker_agents import get_worker
            # Ask AI which workers to use
            prompt = (
                f"{self.system_prompt}\n\n"
                f"Task: {task}\n\n"
                "Which worker agents should handle this? "
                "Respond with a JSON array of worker names only, or [] if none apply."
            )
            async for event in provider_registry.route_request(
                messages=[{"role": "user", "content": prompt}],
                provider_name=self._provider,
                model=self._model,
                temperature=0.3,
                stream=False,
            ):
                if event["type"] == "done":
                    content = event.get("content", "").strip()
                    try:
                        workers = json.loads(content)
                        if isinstance(workers, list) and workers:
                            results = []
                            for w in workers:
                                worker = get_worker(w)
                                if worker:
                                    r = await worker.execute(task)
                                    results.append(r)
                            if results:
                                return "\n\n".join(results)
                    except (json.JSONDecodeError, Exception):
                        pass
        except Exception as e:
            logger.debug("Worker delegation failed: %s", e)
        return None
    
    async def _handle_directly(self, task: str) -> str:
        """Handle the task directly using AI."""
        prompt = f"{self.system_prompt}\n\nTask: {task}"
        result = ""
        async for event in provider_registry.route_request(
            messages=[{"role": "user", "content": prompt}],
            provider_name=self._provider,
            model=self._model,
            temperature=0.5,
            stream=False,
        ):
            if event["type"] == "done":
                result = event.get("content", "")
        return result


# ── Concrete Manager Agents ──

class EngineeringManager(ManagerAgent):
    def __init__(self):
        super().__init__(
            name="Engineering Manager",
            role_description="Manages software development tasks",
            system_prompt=(
                "You are the Engineering Manager. You oversee software development, "
                "code reviews, architecture decisions, and technical implementation. "
                "Delegate coding tasks to Software Engineer and Backend Engineer workers. "
                "Ensure code quality, best practices, and proper testing."
            ),
        )


class ResearchManager(ManagerAgent):
    def __init__(self):
        super().__init__(
            name="Research Manager",
            role_description="Manages information gathering and analysis",
            system_prompt=(
                "You are the Research Manager. You coordinate web research, "
                "data analysis, and information synthesis. "
                "Use Research Agent and Browser Agent for data collection. "
                "Verify facts from multiple sources and provide citations."
            ),
        )


class AutomationManager(ManagerAgent):
    def __init__(self):
        super().__init__(
            name="Automation Manager",
            role_description="Manages workflow automation and scheduling",
            system_prompt=(
                "You are the Automation Manager. You design and manage automated "
                "workflows, scheduled tasks, triggers, and integrations. "
                "Use Web Automation Agent and Playwright Agent for browser automation. "
                "Ensure reliable execution with proper error handling."
            ),
        )


class MarketingManager(ManagerAgent):
    def __init__(self):
        super().__init__(
            name="Marketing Manager",
            role_description="Manages marketing content and strategy",
            system_prompt=(
                "You are the Marketing Manager. You oversee content creation, "
                "marketing strategy, social media, and brand messaging. "
                "Coordinate with Content Manager and use analytics for insights. "
                "Ensure consistent brand voice across all channels."
            ),
        )


class SalesManager(ManagerAgent):
    def __init__(self):
        super().__init__(
            name="Sales Manager",
            role_description="Manages sales pipeline and outreach",
            system_prompt=(
                "You are the Sales Manager. You oversee the entire sales process — "
                "lead generation, qualification, outreach, proposals, and follow-ups. "
                "Coordinate with Lead Finder, CRM Manager, and Proposal Generator. "
                "Track pipeline metrics and optimize conversion."
            ),
        )


class SecurityManager(ManagerAgent):
    def __init__(self):
        super().__init__(
            name="Security Manager",
            role_description="Manages security assessment and compliance",
            system_prompt=(
                "You are the Security Manager. You oversee security audits, "
                "vulnerability assessments, and compliance checks. "
                "Use Security Agent for automated scanning. "
                "Follow OWASP best practices and industry standards."
            ),
        )


class ContentManager(ManagerAgent):
    def __init__(self):
        super().__init__(
            name="Content Manager",
            role_description="Manages content writing and editing",
            system_prompt=(
                "You are the Content Manager. You oversee content strategy, "
                "writing, editing, and documentation. "
                "Ensure high-quality, on-brand content across all formats. "
                "Coordinate with writers and editors for production."
            ),
        )


class CustomerSupportManager(ManagerAgent):
    def __init__(self):
        super().__init__(
            name="Customer Support Manager",
            role_description="Manages customer support and issue resolution",
            system_prompt=(
                "You are the Customer Support Manager. You handle customer inquiries, "
                "issue resolution, and support ticket management. "
                "Be empathetic, thorough, and solution-oriented. "
                "Escalate complex issues appropriately."
            ),
        )


# ── Registry ──

_manager_registry: Dict[str, ManagerAgent] = {}


def register_managers():
    """Register all manager agents."""
    managers = [
        EngineeringManager(),
        ResearchManager(),
        AutomationManager(),
        MarketingManager(),
        SalesManager(),
        SecurityManager(),
        ContentManager(),
        CustomerSupportManager(),
    ]
    for m in managers:
        _manager_registry[m.name] = m
    logger.info("Registered %d manager agents", len(managers))


def get_manager(name: str) -> Optional[ManagerAgent]:
    """Get a manager agent by name."""
    return _manager_registry.get(name)


def list_managers() -> List[Dict[str, Any]]:
    """List all registered manager agents."""
    return [
        {"name": m.name, "role": m.role_description}
        for m in _manager_registry.values()
    ]
