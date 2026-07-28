"""
Zentar Intelligence — Prompt Engine

Template-based prompt rendering with variables, sections,
and conditional blocks for dynamic prompt construction.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from app.core.config import get_settings

logger = logging.getLogger("zentar.agents.prompts")

settings = get_settings()


class PromptTemplate:
    """A prompt template with variable substitution and sections."""

    def __init__(self, template: str, name: Optional[str] = None):
        self.template = template
        self.name = name or "prompt"
        self._variables: Dict[str, Any] = {}

    def set(self, key: str, value: Any):
        """Set a template variable."""
        self._variables[key] = value
        return self

    def set_all(self, variables: Dict[str, Any]):
        """Set multiple template variables."""
        self._variables.update(variables)
        return self

    def render(self, **kwargs) -> str:
        """Render the template with variable substitution.

        Supports:
        - {{ variable }} — simple variable substitution
        - {% if var %}...{% endif %} — conditional blocks
        - {% for item in list %}...{% endfor %} — iteration
        """
        variables = {**self._variables, **kwargs}
        text = self.template

        # Process conditionals: {% if var %}content{% endif %}
        def replace_conditional(match):
            full = match.group(0)
            inner_match = re.match(
                r"\{% if (\w+) %\}(.*?)\{% endif %\}",
                full,
                re.DOTALL,
            )
            if inner_match:
                var_name = inner_match.group(1)
                content = inner_match.group(2)
                if variables.get(var_name):
                    return self._render_template(content, variables)
            return ""

        text = re.sub(r"\{% if \w+ %\}.*?\{% endif %\}", replace_conditional, text, flags=re.DOTALL)

        # Process for loops: {% for item in list %}content{% endfor %}
        def replace_for(match):
            full = match.group(0)
            inner_match = re.match(
                r"\{% for (\w+) in (\w+) %\}(.*?)\{% endfor %\}",
                full,
                re.DOTALL,
            )
            if inner_match:
                item_name = inner_match.group(1)
                list_name = inner_match.group(2)
                content = inner_match.group(3)
                items = variables.get(list_name, [])
                if isinstance(items, (list, dict)):
                    parts = []
                    if isinstance(items, list):
                        for item in items:
                            v = {**variables, item_name: item}
                            parts.append(self._render_template(content, v))
                    elif isinstance(items, dict):
                        for key, value in items.items():
                            v = {**variables, item_name: key, f"{item_name}_value": value}
                            parts.append(self._render_template(content, v))
                    return "\n".join(parts)
            return ""

        text = re.sub(
            r"\{% for \w+ in \w+ %\}.*?\{% endfor %\}",
            replace_for,
            text,
            flags=re.DOTALL,
        )

        # Replace {{ variables }}
        text = self._render_template(text, variables)
        return text

    def _render_template(self, text: str, variables: Dict[str, Any]) -> str:
        """Replace {{ variable }} placeholders."""
        def replace_var(match):
            var_name = match.group(1).strip()
            value = variables.get(var_name, match.group(0))
            if value is None:
                return ""
            return str(value)

        return re.sub(r"\{\{ (\w+) \}\}", replace_var, text)


class SystemPromptBuilder:
    """Builds system prompts from modular sections."""

    def __init__(self):
        self._sections: List[Dict[str, Any]] = []

    def add_section(
        self,
        name: str,
        content: str,
        condition: Optional[bool] = True,
    ):
        """Add a conditional section to the prompt."""
        self._sections.append({
            "name": name,
            "content": content,
            "condition": condition,
        })
        return self

    def add_persona(self, persona: str):
        """Add a persona definition section."""
        return self.add_section(
            "persona",
            f"You are {persona}. Respond in character while being helpful.",
            True,
        )

    def add_capabilities(self, capabilities: List[str]):
        """Add a capabilities section listing what the agent can do."""
        content = "You have the following capabilities:\n" + "\n".join(
            f"- {cap}" for cap in capabilities
        )
        return self.add_section("capabilities", content, True)

    def add_tools_guide(self, tools: List[str]):
        """Add a guide about available tools."""
        if not tools:
            return self
        content = (
            "You have access to the following tools. Use them when appropriate:\n"
            + "\n".join(f"- {t}" for t in tools)
        )
        return self.add_section("tools", content, True)

    def add_memory_context(self, memories: List[str]):
        """Add memory context to the prompt."""
        if not memories:
            return self
        content = "## Relevant Memories\n" + "\n".join(f"- {m}" for m in memories)
        return self.add_section("memories", content, True)

    def add_rules(self, rules: List[str]):
        """Add behavioral rules."""
        content = "## Rules\n" + "\n".join(f"{i+1}. {r}" for i, r in enumerate(rules))
        return self.add_section("rules", content, True)

    def add_skill_prompts(self, skill_prompts: List[str]):
        """Add skill-specific system prompts."""
        if not skill_prompts:
            return self
        content = "## Active Skills\n" + "\n\n".join(skill_prompts)
        return self.add_section("skills", content, True)

    def build(self, separator: str = "\n\n") -> str:
        """Build the final system prompt from all sections."""
        sections = [s for s in self._sections if s["condition"]]
        return separator.join(s["content"] for s in sections)

    def clear(self):
        """Clear all sections."""
        self._sections = []


class PromptLibrary:
    """Library of pre-defined prompt templates."""

    @staticmethod
    def coding_assistant() -> str:
        return (
            "You are an expert coding assistant. You help users write, debug, "
            "and understand code. You provide clear, concise explanations and "
            "working code examples. You follow best practices and consider "
            "edge cases. When you're unsure, you say so rather than guessing."
        )

    @staticmethod
    def automation_agent() -> str:
        return (
            "You are an automation agent that controls Android device operations. "
            "You can click, scroll, type, navigate between apps, and read screen content. "
            "Always respect user privacy and only perform actions the user has authorized. "
            "Confirm before performing irreversible actions."
        )

    @staticmethod
    def research_agent() -> str:
        return (
            "You are a research assistant. You synthesize information from multiple sources "
            "to provide accurate, well-cited answers. You acknowledge uncertainty "
            "and distinguish between established facts and emerging findings."
        )

    @staticmethod
    def data_analyst() -> str:
        return (
            "You are a data analyst assistant. You help users explore, analyze, and visualize data. "
            "You write clean analysis code, explain your methodology, and highlight "
            "key findings and limitations. You prefer statistical rigor over speculation."
        )

    @staticmethod
    def default_rules() -> List[str]:
        return [
            "Respond in a helpful, accurate, and safe manner.",
            "If you don't know something, say so — don't make up information.",
            "Use tools when they would genuinely help, not for every query.",
            "Respect user privacy and data confidentiality at all times.",
            "Ask clarifying questions when the user's request is ambiguous.",
            "Provide code in proper markdown code blocks with language tags.",
            "Break down complex tasks into manageable steps.",
        ]
