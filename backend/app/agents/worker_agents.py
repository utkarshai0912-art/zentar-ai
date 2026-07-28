"""
Zentar Intelligence — Worker Agents

Specialized worker agents that execute specific tasks.
Each worker is an expert in a narrow domain.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from app.services.ai_service import provider_registry

logger = logging.getLogger("zentar.agents.workers")


class WorkerAgent:
    """Base class for specialized worker agents."""
    
    def __init__(self, name: str, expertise: str, system_prompt: str):
        self.name = name
        self.expertise = expertise
        self.system_prompt = system_prompt
        self._provider: Optional[str] = None
        self._model: Optional[str] = None
    
    def configure(self, provider: Optional[str] = None, model: Optional[str] = None):
        self._provider = provider
        self._model = model
    
    async def execute(self, task: str) -> str:
        """Execute a task within this worker's domain of expertise."""
        prompt = f"{self.system_prompt}\n\nTask: {task}"
        result = ""
        async for event in provider_registry.route_request(
            messages=[{"role": "user", "content": prompt}],
            provider_name=self._provider,
            model=self._model,
            temperature=0.3,
            stream=False,
        ):
            if event["type"] == "done":
                result = event.get("content", "")
        return result


# ── All Worker Agents ──

class SoftwareEngineerWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Software Engineer",
            expertise="Writing high-quality code across languages",
            system_prompt="You are a senior software engineer. Write clean, efficient, well-tested code. Follow SOLID principles and language-specific best practices.",
        )


class BackendEngineerWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Backend Engineer",
            expertise="Backend API and server development",
            system_prompt="You are a backend engineer expert in Python, FastAPI, SQLAlchemy, and REST APIs. Design scalable APIs, optimize database queries, and ensure security.",
        )


class FrontendEngineerWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Frontend Engineer",
            expertise="Frontend UI and component development",
            system_prompt="You are a frontend engineer expert in React, TypeScript, and modern CSS. Build responsive, accessible UI components with clean state management.",
        )


class DatabaseEngineerWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Database Engineer",
            expertise="Database design and optimization",
            system_prompt="You are a database engineer expert in PostgreSQL, SQLAlchemy, and data modeling. Design efficient schemas, write optimized queries, and manage migrations.",
        )


class DevOpsEngineerWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="DevOps Engineer",
            expertise="Deployment, CI/CD, and infrastructure",
            system_prompt="You are a DevOps engineer expert in Railway, Docker, CI/CD pipelines, and cloud infrastructure. Automate deployments and ensure reliability.",
        )


class ResearchAgentWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Research Agent",
            expertise="Web research and information synthesis",
            system_prompt="You are a research agent. Find accurate, up-to-date information from multiple sources. Synthesize findings with proper citations. Distinguish facts from opinions.",
        )


class BrowserAgentWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Browser Agent",
            expertise="Web browsing and data extraction",
            system_prompt="You are a browser automation agent. Navigate websites, extract data, fill forms, and take screenshots. Use the browser tools responsibly.",
        )


class WebAutomationWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Web Automation Agent",
            expertise="Automating web workflows and processes",
            system_prompt="You are a web automation expert. Automate multi-step web workflows, handle authentication, manage sessions, and extract structured data from websites.",
        )


class PlaywrightWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Playwright Agent",
            expertise="Browser testing and automation with Playwright",
            system_prompt="You are a Playwright automation expert. Write and execute browser tests, automate complex web interactions, handle iframes and popups, and generate reports.",
        )


class MemoryWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Memory Agent",
            expertise="Memory management and knowledge retention",
            system_prompt="You are a memory management agent. Store and retrieve information efficiently. Organize knowledge for easy recall. Manage short-term and long-term memory.",
        )


class KnowledgeWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Knowledge Agent",
            expertise="Knowledge base management and retrieval",
            system_prompt="You are a knowledge management agent. Build and maintain knowledge bases. Index information for semantic search. Ensure knowledge is accurate and up-to-date.",
        )


class OCRAgentWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="OCR Agent",
            expertise="Optical character recognition and text extraction from images",
            system_prompt="You are an OCR specialist. Extract text from images, scanned documents, and PDFs. Handle multiple languages and poor-quality scans.",
        )


class ImageWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Image Agent",
            expertise="Image analysis and generation",
            system_prompt="You are an image analysis and generation agent. Describe images, extract information from visuals, generate images based on descriptions, and edit images.",
        )


class SpeechWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Speech Agent",
            expertise="Speech-to-text and text-to-speech processing",
            system_prompt="You are a speech processing agent. Transcribe audio to text, generate speech from text, detect languages, and handle multiple audio formats.",
        )


class TranslationWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Translation Agent",
            expertise="Language translation with context awareness",
            system_prompt="You are a professional translator. Translate between languages preserving meaning, tone, and cultural context. Handle idioms and technical terminology.",
        )


class CodingWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Coding Agent",
            expertise="General coding assistance and problem-solving",
            system_prompt="You are a coding assistant. Help with algorithms, data structures, code reviews, debugging, and best practices across all programming languages.",
        )


class DebugWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Debug Agent",
            expertise="Debugging and root cause analysis",
            system_prompt="You are a debugging specialist. Analyze error messages, stack traces, and logs. Identify root causes and propose fixes. Use systematic elimination.",
        )


class TestingWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Testing Agent",
            expertise="Software testing and quality assurance",
            system_prompt="You are a testing specialist. Write unit tests, integration tests, and end-to-end tests. Perform regression testing and ensure code coverage.",
        )


class SecurityWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Security Agent",
            expertise="Security auditing and vulnerability assessment",
            system_prompt="You are a security specialist. Identify OWASP Top 10 vulnerabilities, assess authentication/authorization, check for injection flaws, and recommend fixes.",
        )


class LeadFinderWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Lead Finder Agent",
            expertise="Business lead discovery and qualification",
            system_prompt="You are a lead generation specialist. Find potential business leads through web research. Qualify leads based on criteria. Collect contact information responsibly.",
        )


class CRMManagerWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="CRM Agent",
            expertise="Customer relationship management",
            system_prompt="You are a CRM specialist. Manage customer data, track interactions, update contact records, and generate reports on sales pipeline and customer engagement.",
        )


class EmailWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Email Agent",
            expertise="Email composition and management",
            system_prompt="You are an email specialist. Compose professional emails, manage email campaigns, personalize outreach, and track responses.",
        )


class WhatsAppWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="WhatsApp Agent",
            expertise="WhatsApp Business messaging",
            system_prompt="You are a WhatsApp Business specialist. Compose and send WhatsApp messages, manage templates, handle customer inquiries, and send notifications.",
        )


class ProposalGeneratorWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Proposal Generator",
            expertise="Business proposal and quote generation",
            system_prompt="You are a proposal generation specialist. Create professional business proposals, quotes, and estimates. Tailor content to client needs and highlight value propositions.",
        )


class MeetingSchedulerWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Meeting Scheduler",
            expertise="Meeting scheduling and calendar management",
            system_prompt="You are a scheduling specialist. Coordinate meeting times across time zones, send calendar invites, manage availability, and handle rescheduling.",
        )


class AnalyticsWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Analytics Agent",
            expertise="Data analytics and business intelligence",
            system_prompt="You are an analytics specialist. Analyze data, create visualizations, identify trends, and generate actionable insights. Use statistical methods appropriately.",
        )


class WorkflowWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Workflow Agent",
            expertise="Workflow design and automation",
            system_prompt="You are a workflow automation specialist. Design automated workflows, set up triggers and conditions, integrate services, and ensure reliable execution.",
        )


class TaskPlannerWorker(WorkerAgent):
    def __init__(self):
        super().__init__(
            name="Task Planner",
            expertise="Task planning and project management",
            system_prompt="You are a task planning specialist. Break down projects into tasks, estimate effort, set priorities, track dependencies, and manage timelines.",
        )


# ── Registry ──

_worker_registry: Dict[str, WorkerAgent] = {}


def register_workers():
    """Register all worker agents."""
    workers = [
        SoftwareEngineerWorker(),
        BackendEngineerWorker(),
        FrontendEngineerWorker(),
        DatabaseEngineerWorker(),
        DevOpsEngineerWorker(),
        ResearchAgentWorker(),
        BrowserAgentWorker(),
        WebAutomationWorker(),
        PlaywrightWorker(),
        MemoryWorker(),
        KnowledgeWorker(),
        OCRAgentWorker(),
        ImageWorker(),
        SpeechWorker(),
        TranslationWorker(),
        CodingWorker(),
        DebugWorker(),
        TestingWorker(),
        SecurityWorker(),
        LeadFinderWorker(),
        CRMManagerWorker(),
        EmailWorker(),
        WhatsAppWorker(),
        ProposalGeneratorWorker(),
        MeetingSchedulerWorker(),
        AnalyticsWorker(),
        WorkflowWorker(),
        TaskPlannerWorker(),
    ]
    for w in workers:
        _worker_registry[w.name] = w
    logger.info("Registered %d worker agents", len(workers))


def get_worker(name: str) -> Optional[WorkerAgent]:
    """Get a worker agent by name."""
    return _worker_registry.get(name)


def list_workers() -> List[Dict[str, Any]]:
    """List all registered worker agents."""
    return [
        {"name": w.name, "expertise": w.expertise}
        for w in _worker_registry.values()
    ]
