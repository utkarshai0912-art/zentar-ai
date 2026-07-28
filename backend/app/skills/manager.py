"""
Zentar Intelligence — Skills Manager

Manages skill lifecycle — discovery, activation, and execution.
Skills are composable AI capabilities with their own prompts and tools.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from app.core.config import get_settings

logger = logging.getLogger("zentar.skills.manager")

settings = get_settings()


class SkillDefinition:
    """Definition of a skill that can be activated."""

    def __init__(
        self,
        skill_id: str,
        name: str,
        display_name: str,
        description: str,
        category: str = "general",
        system_prompt: Optional[str] = None,
        tools: Optional[List[str]] = None,
        permissions: Optional[List[str]] = None,
        preferred_provider: Optional[str] = None,
        preferred_model: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        required_plugins: Optional[List[str]] = None,
        memory_rules: Optional[Dict[str, Any]] = None,
        icon: Optional[str] = None,
        version: str = "1.0.0",
    ):
        self.skill_id = skill_id
        self.name = name
        self.display_name = display_name
        self.description = description
        self.category = category
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.permissions = permissions or []
        self.preferred_provider = preferred_provider
        self.preferred_model = preferred_model
        self.dependencies = dependencies or []
        self.required_plugins = required_plugins or []
        self.memory_rules = memory_rules or {}
        self.icon = icon
        self.version = version
        self.is_active = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "tools": self.tools,
            "permissions": self.permissions,
            "preferred_provider": self.preferred_provider,
            "preferred_model": self.preferred_model,
            "dependencies": self.dependencies,
            "required_plugins": self.required_plugins,
            "icon": self.icon,
            "version": self.version,
            "is_active": self.is_active,
        }


class SkillManager:
    """Manages skills — activation, deactivation, and execution."""

    def __init__(self):
        self._skills: Dict[str, SkillDefinition] = {}
        self._active_skills: Dict[str, SkillDefinition] = {}
        self._categories: Dict[str, List[str]] = {}

    def register(self, skill: SkillDefinition):
        """Register a skill definition."""
        self._skills[skill.skill_id] = skill
        if skill.category not in self._categories:
            self._categories[skill.category] = []
        self._categories[skill.category].append(skill.skill_id)
        logger.info("Registered skill: %s (%s)", skill.display_name, skill.category)

    def register_many(self, skills: List[SkillDefinition]):
        """Register multiple skills."""
        for skill in skills:
            self.register(skill)

    def unregister(self, skill_id: str):
        """Unregister a skill."""
        skill = self._skills.pop(skill_id, None)
        if skill:
            self._active_skills.pop(skill_id, None)
            if skill.category in self._categories:
                self._categories[skill.category].remove(skill_id)

    def activate(self, skill_id: str) -> bool:
        """Activate a skill for use."""
        skill = self._skills.get(skill_id)
        if not skill:
            return False

        # Check dependencies
        for dep in skill.dependencies:
            if dep not in self._active_skills:
                logger.warning("Cannot activate %s: dependency %s not active", skill_id, dep)
                return False

        skill.is_active = True
        self._active_skills[skill_id] = skill
        logger.info("Activated skill: %s", skill.display_name)
        return True

    def deactivate(self, skill_id: str) -> bool:
        """Deactivate a skill."""
        skill = self._active_skills.pop(skill_id, None)
        if skill:
            skill.is_active = False
            logger.info("Deactivated skill: %s", skill.display_name)
            return True
        return False

    def get(self, skill_id: str) -> Optional[SkillDefinition]:
        """Get a skill definition."""
        return self._skills.get(skill_id)

    def list_skills(
        self,
        category: Optional[str] = None,
        active_only: bool = False,
    ) -> List[SkillDefinition]:
        """List skills with optional filtering."""
        skills = list(self._skills.values())

        if category:
            names = self._categories.get(category, [])
            skills = [s for s in skills if s.skill_id in names]

        if active_only:
            skills = [s for s in skills if s.is_active]

        return skills

    def list_categories(self) -> List[str]:
        """List all skill categories."""
        return list(self._categories.keys())

    def get_combined_prompt(self, active_only: bool = True) -> Optional[str]:
        """Get combined system prompt from active skills."""
        skills = self.list_skills(active_only=active_only) if active_only else []
        prompts = [s.system_prompt for s in skills if s.system_prompt]
        if not prompts:
            return None
        return "\n\n".join(prompts)

    def get_combined_tools(self, active_only: bool = True) -> List[str]:
        """Get combined tool list from active skills."""
        skills = self.list_skills(active_only=active_only) if active_only else []
        tools = set()
        for s in skills:
            tools.update(s.tools)
        return list(tools)

    def get_stats(self) -> Dict[str, Any]:
        """Get skill manager statistics."""
        return {
            "total_skills": len(self._skills),
            "active_skills": len(self._active_skills),
            "categories": {cat: len(names) for cat, names in self._categories.items()},
        }


# Global skill manager
skill_manager = SkillManager()


# ──────────────────────────────────────────
# Built-in Skills Registration
# ──────────────────────────────────────────

_BASE_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "prompts")


def _load_prompt(filename: str) -> str:
    """Load a system prompt from the prompts directory."""
    path = os.path.join(_BASE_PROMPT_DIR, filename)
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        logger.warning("Prompt file not found: %s", path)
        return ""


def register_builtin_skills():
    """Register default skills."""
    # Load base-agent prompt from external file
    base_agent_prompt = _load_prompt("base-agent.md")

    skill_manager.register_many([
        SkillDefinition(
            skill_id="code-assist",
            name="code-assist",
            display_name="Code Assistant",
            description="Helps write, debug, and review code across languages",
            category="coding",
            system_prompt="You are an expert programmer. Write clean, efficient, well-documented code. Follow language-specific best practices and design patterns.",
            tools=["read_file", "write_file", "run_command", "list_files", "web_search"],
            permissions=["filesystem", "network"],
            preferred_provider="openai",
            preferred_model="gpt-4o",
        ),
        SkillDefinition(
            skill_id="web-research",
            name="web-research",
            display_name="Web Research",
            description="Searches and synthesizes information from the web",
            category="research",
            system_prompt="You are a research assistant. Find accurate, up-to-date information and cite your sources. Distinguish between facts and opinions.",
            tools=["web_search"],
            permissions=["network"],
            preferred_provider="openai",
            preferred_model="gpt-4o",
        ),
        SkillDefinition(
            skill_id="data-analysis",
            name="data-analysis",
            display_name="Data Analysis",
            description="Analyzes data, creates visualizations, and extracts insights",
            category="data",
            system_prompt="You are a data analyst. Help users explore, clean, analyze, and visualize data. Explain your methodology and highlight key findings.",
            tools=["read_file", "write_file", "run_command"],
            permissions=["filesystem"],
            preferred_provider="openai",
            preferred_model="gpt-4o",
        ),
        SkillDefinition(
            skill_id="content-writer",
            name="content-writer",
            display_name="Content Writer",
            description="Helps write and edit content, from emails to articles",
            category="writing",
            system_prompt="You are a professional writer. Adapt your tone and style to the audience. Write clearly and persuasively.",
            tools=[],
            permissions=[],
            preferred_provider="openai",
            preferred_model="gpt-4o",
        ),
        SkillDefinition(
            skill_id="security-audit",
            name="security-audit",
            display_name="Security Auditor",
            description="Reviews code for security vulnerabilities",
            category="security",
            system_prompt="You are a security expert. Review code for OWASP Top 10 vulnerabilities, injection flaws, authentication issues, and insecure configurations. Be thorough and practical.",
            tools=["read_file", "web_search"],
            permissions=["filesystem", "network"],
            preferred_provider="anthropic",
            preferred_model="claude-sonnet-4-20250514",
        ),
        SkillDefinition(
            skill_id="android-auto",
            name="android-auto",
            display_name="Android Automation",
            description="Controls Android device UI through accessibility services",
            category="automation",
            system_prompt="You are an Android automation agent. You can interact with the device screen. Always confirm before irreversible actions.",
            tools=["click", "type_text", "scroll", "go_back", "go_home", "read_screen"],
            permissions=["accessibility", "notifications"],
            preferred_provider="openai",
            preferred_model="gpt-4o",
        ),
        SkillDefinition(
            skill_id="translator",
            name="translator",
            display_name="Translator",
            description="Translates text between languages with context awareness",
            category="writing",
            system_prompt="You are a professional translator. Preserve meaning, tone, and cultural context. Offer alternatives for ambiguous phrases.",
            tools=[],
            permissions=[],
            preferred_provider="openai",
            preferred_model="gpt-4o",
        ),
        # ── Claude Fable 5 Skills ──
        SkillDefinition(
            skill_id="docx",
            name="docx",
            display_name="Word Document Expert",
            description="Creates, reads, edits, and manipulates Word documents (.docx) with professional formatting including TOC, headings, page numbers, letterheads, images, tracked changes, and templates (.dotx)",
            category="document",
            system_prompt="You are an expert at creating and editing Word documents. You handle .docx and .dotx files with professional formatting — tables of contents, headings, page numbers, letterheads, images, tracked changes. You extract and reorganize content, perform find-and-replace, and produce polished deliverables.",
            tools=["read_file", "write_file", "list_files"],
            permissions=["filesystem"],
            preferred_provider="openai",
            preferred_model="gpt-4o",
        ),
        SkillDefinition(
            skill_id="pdf",
            name="pdf",
            display_name="PDF Expert",
            description="Full PDF lifecycle: read/extract text/tables, merge, split, rotate, watermark, create new PDFs, fill forms, encrypt/decrypt, OCR scanned PDFs, and extract images",
            category="document",
            system_prompt="You are an expert at everything PDF-related. You can read and extract text/tables from PDFs, combine or merge multiple PDFs, split PDFs apart, rotate pages, add watermarks, create new PDFs from scratch, fill PDF forms, encrypt and decrypt PDFs, extract embedded images, and perform OCR on scanned PDFs to make them searchable.",
            tools=["read_file", "write_file", "run_command"],
            permissions=["filesystem"],
            preferred_provider="openai",
            preferred_model="gpt-4o",
        ),
        SkillDefinition(
            skill_id="pptx",
            name="pptx",
            display_name="PowerPoint Expert",
            description="Creates, reads, edits slide decks and presentations (.pptx, .potx) with layouts, speaker notes, comments, and templates",
            category="document",
            system_prompt="You are an expert at creating and editing PowerPoint presentations. You handle .pptx and .potx files — creating slide decks and pitch decks, reading and extracting text, editing existing presentations, combining or splitting slide files, working with templates/potx, layouts, speaker notes, and comments.",
            tools=["read_file", "write_file", "list_files"],
            permissions=["filesystem"],
            preferred_provider="openai",
            preferred_model="gpt-4o",
        ),
        SkillDefinition(
            skill_id="xlsx",
            name="xlsx",
            display_name="Spreadsheet Expert",
            description="Creates, reads, edits spreadsheets (.xlsx, .xlsm, .csv, .tsv) with formulas, formatting, charts, data cleaning, and conversion between tabular formats",
            category="data",
            system_prompt="You are an expert at working with spreadsheets. You can create, read, edit, and fix .xlsx, .xlsm, .xltx, .csv, and .tsv files. You handle formulas, formatting, charting, data cleaning, and conversion between tabular file formats. You restructure messy data into proper spreadsheets.",
            tools=["read_file", "write_file", "run_command"],
            permissions=["filesystem"],
            preferred_provider="openai",
            preferred_model="gpt-4o",
        ),
        SkillDefinition(
            skill_id="frontend-design",
            name="frontend-design",
            display_name="Frontend Design",
            description="Guidance for distinctive, intentional visual design — aesthetic direction, typography, and non-templated UI choices",
            category="coding",
            system_prompt="You have expertise in distinctive, intentional visual design. You provide guidance on aesthetic direction, typography, color systems, spacing, and making design choices that don't read as templated defaults. You help build UI that feels intentional and cohesive.",
            tools=[],
            permissions=[],
            preferred_provider="openai",
            preferred_model="gpt-4o",
        ),
        SkillDefinition(
            skill_id="product-knowledge",
            name="product-knowledge",
            display_name="Product Knowledge",
            description="Accurate, up-to-date information about AI products — capabilities, pricing, API usage, SDKs, and platform features",
            category="research",
            system_prompt="You provide accurate information about AI products and platforms. You cover API capabilities, pricing tiers, model features, SDK usage, rate limits, streaming, batch processing, function calling/tool use, and platform-specific configuration. You verify facts rather than relying on potentially outdated training data.",
            tools=["web_search"],
            permissions=["network"],
            preferred_provider="openai",
            preferred_model="gpt-4o",
        ),
        SkillDefinition(
            skill_id="skill-creator",
            name="skill-creator",
            display_name="Skill Creator",
            description="Creates, modifies, and optimizes skills — runs evals, benchmarks performance, and optimizes skill descriptions for triggering accuracy",
            category="general",
            system_prompt="You are a skill engineering expert. You create new skills from scratch, modify and improve existing skills, and measure skill performance. You run evals to test skills, benchmark performance with variance analysis, and optimize skill descriptions for better triggering accuracy.",
            tools=["read_file", "write_file", "list_files", "run_command"],
            permissions=["filesystem"],
            preferred_provider="openai",
            preferred_model="gpt-4o",
        ),
        SkillDefinition(
            skill_id="morning-brief",
            name="morning-brief",
            display_name="Morning Brief",
            description="Renders a styled morning brief as an HTML artifact or sets it up as a recurring weekday task",
            category="general",
            system_prompt="You create morning briefings as styled HTML artifacts. You organize information clearly — date, weather, schedule, reminders, and key highlights. You set up recurring weekday tasks when requested.",
            tools=["write_file"],
            permissions=[],
            preferred_provider="openai",
            preferred_model="gpt-4o",
        ),
        # ── Base Agent Skill (loaded from prompts/base-agent.md) ──
        SkillDefinition(
            skill_id="base-agent",
            name="base-agent",
            display_name="Claude Fable 5 Base Agent",
            description="Core AI agent personality and behavior — warm, knowledgeable, safety-conscious, evenhanded, with strong ethics and professional communication",
            category="core",
            system_prompt=base_agent_prompt or (
                "You are Claude Fable 5, an AI assistant created by Anthropic. "
                "You have a warm, respectful tone — treating people with kindness "
                "without making negative assumptions about their judgment or abilities."
            ),
            tools=["web_search", "calculator", "current_time"],
            permissions=["network"],
            preferred_provider="anthropic",
            preferred_model="claude-sonnet-4-20250514",
        ),
    ])
