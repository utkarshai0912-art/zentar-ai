"""
Zentar Intelligence — WSHobson Agent Marketplace Integration

Reads agent definitions from the wshobson/agents marketplace repo
and makes them available as installable agents in Zentar.
"""

import json
import logging
import os
import re
import yaml
import uuid
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("zentar.agents.marketplace")

_MARKETPLACE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    ".wshobson-agents",
)


class MarketplaceAgent:
    """An agent from the wshobson marketplace."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        display_name: str,
        plugin: str,
        plugin_category: str,
        description: str,
        system_prompt: str,
        model_tier: str,
        tools: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ):
        self.agent_id = agent_id
        self.name = name
        self.display_name = display_name
        self.plugin = plugin
        self.plugin_category = plugin_category
        self.description = description
        self.system_prompt = system_prompt
        self.model_tier = model_tier
        self.tools = tools or []
        self.tags = tags or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "display_name": self.display_name,
            "plugin": self.plugin,
            "plugin_category": self.plugin_category,
            "description": self.description[:200],
            "system_prompt_length": len(self.system_prompt),
            "model_tier": self.model_tier,
            "tools": self.tools,
            "tags": self.tags,
        }


class WSMarketplaceReader:
    """Reads agent definitions from the wshobson/agents marketplace."""

    def __init__(self):
        self._agents: Dict[str, MarketplaceAgent] = {}
        self._plugins: Dict[str, Dict[str, Any]] = {}
        self._loaded = False

    def load_all(self):
        """Scan the marketplace directory and load all agent definitions."""
        if self._loaded:
            return
        plugins_dir = os.path.join(_MARKETPLACE_PATH, "plugins")
        if not os.path.isdir(plugins_dir):
            logger.warning("Marketplace plugins directory not found: %s", plugins_dir)
            return

        for plugin_name in sorted(os.listdir(plugins_dir)):
            plugin_path = os.path.join(plugins_dir, plugin_name)
            if not os.path.isdir(plugin_path):
                continue

            plugin_info = self._read_plugin_info(plugin_name, plugin_path)
            self._plugins[plugin_name] = plugin_info

            agents_dir = os.path.join(plugin_path, "agents")
            if os.path.isdir(agents_dir):
                for agent_file in sorted(os.listdir(agents_dir)):
                    if not agent_file.endswith(".md"):
                        continue
                    agent_path = os.path.join(agents_dir, agent_file)
                    agent = self._read_agent(agent_path, plugin_name, plugin_info)
                    if agent:
                        self._agents[agent.agent_id] = agent

        self._loaded = True
        logger.info(
            "Loaded %d agents from %d plugins in marketplace",
            len(self._agents),
            len(self._plugins),
        )

    def _read_plugin_info(self, plugin_name: str, plugin_path: str) -> Dict[str, Any]:
        """Read plugin metadata from plugin.json."""
        plugin_json = os.path.join(plugin_path, ".claude-plugin", "plugin.json")
        info = {"name": plugin_name, "category": "uncategorized", "description": ""}
        if os.path.isfile(plugin_json):
            try:
                with open(plugin_json) as f:
                    data = json.load(f)
                    info["name"] = data.get("name", plugin_name)
                    info["description"] = data.get("description", "")
                    info["version"] = data.get("version", "1.0.0")
                    info["author"] = data.get("author", {}).get("name", "Unknown")
            except (json.JSONDecodeError, Exception) as e:
                logger.debug("Failed to read plugin.json for %s: %s", plugin_name, e)

        # Try to determine category from path or README
        readme = os.path.join(plugin_path, "README.md")
        if os.path.isfile(readme):
            try:
                with open(readme) as f:
                    first_line = f.readline().strip()
                    if first_line.startswith("# "):
                        info["display_name"] = first_line[2:].strip()
            except Exception:
                pass

        return info

    def _read_agent(self, agent_path: str, plugin_name: str, plugin_info: Dict) -> Optional[MarketplaceAgent]:
        """Read an agent definition from a markdown file with YAML frontmatter."""
        try:
            with open(agent_path) as f:
                content = f.read()
        except Exception as e:
            logger.warning("Failed to read agent %s: %s", agent_path, e)
            return None

        # Parse YAML frontmatter
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not fm_match:
            logger.debug("No frontmatter in %s, skipping", agent_path)
            return None

        try:
            fm = yaml.safe_load(fm_match.group(1))
        except yaml.YAMLError as e:
            logger.debug("YAML error in %s: %s", agent_path, e)
            return None

        if not fm or not isinstance(fm, dict):
            return None

        name = fm.get("name", "")
        if not name:
            name = os.path.splitext(os.path.basename(agent_path))[0]

        description = fm.get("description", "")
        model_tier = fm.get("model", "inherit")
        tools = fm.get("tools")
        if isinstance(tools, str):
            tools = [t.strip() for t in tools.split(",") if t.strip()]

        # Body = everything after frontmatter
        body = content[fm_match.end():].strip()

        # Build full system prompt
        system_prompt = body
        if description:
            system_prompt = f"Description: {description}\n\n{body}"

        agent_id = f"wshobson-{plugin_name}-{name}"

        display_name = " ".join(word.capitalize() for word in name.replace("-", " ").split())

        # Tags
        tags = [plugin_name, plugin_info.get("category", "uncategorized"), model_tier]
        if tools:
            tags.extend(tools)

        return MarketplaceAgent(
            agent_id=agent_id,
            name=name,
            display_name=display_name,
            plugin=plugin_name,
            plugin_category=plugin_info.get("category", "uncategorized"),
            description=description,
            system_prompt=system_prompt,
            model_tier=model_tier,
            tools=tools or [],
            tags=list(set(tags)),
        )

    def list_agents(
        self,
        plugin: Optional[str] = None,
        category: Optional[str] = None,
        model_tier: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
    ) -> List[MarketplaceAgent]:
        """List marketplace agents with optional filtering."""
        if not self._loaded:
            self.load_all()

        agents = list(self._agents.values())

        if plugin:
            agents = [a for a in agents if a.plugin == plugin]
        if category:
            agents = [a for a in agents if a.plugin_category == category]
        if model_tier:
            agents = [a for a in agents if a.model_tier == model_tier]
        if search:
            q = search.lower()
            agents = [
                a for a in agents
                if q in a.name.lower() or q in a.description.lower() or q in a.display_name.lower()
            ]

        return agents[:limit]

    def get_agent(self, agent_id: str) -> Optional[MarketplaceAgent]:
        """Get a specific agent by ID."""
        if not self._loaded:
            self.load_all()
        return self._agents.get(agent_id)

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all available plugins."""
        if not self._loaded:
            self.load_all()
        return [
            {
                "name": name,
                "category": info.get("category", "uncategorized"),
                "description": info.get("description", ""),
                "version": info.get("version", "1.0.0"),
                "author": info.get("author", "Unknown"),
                "agent_count": sum(
                    1 for a in self._agents.values() if a.plugin == name
                ),
            }
            for name, info in self._plugins.items()
        ]

    def list_categories(self) -> List[Dict[str, int]]:
        """List agent categories with counts."""
        if not self._loaded:
            self.load_all()
        counts = {}
        for agent in self._agents.values():
            cat = agent.plugin_category
            counts[cat] = counts.get(cat, 0) + 1
        return [{"category": k, "count": v} for k, v in sorted(counts.items())]

    def install_agent(self, agent_id: str) -> Tuple[bool, str]:
        """Install a marketplace agent into Zentar's custom agent builder."""
        agent = self.get_agent(agent_id)
        if not agent:
            return False, "Agent not found in marketplace"

        from app.agents.custom_agent_builder import custom_agent_builder

        # Map model tier to provider/model
        provider, model = self._map_model_tier(agent.model_tier)

        existing = custom_agent_builder.list_agents()
        if any(a.get("name") == agent.name for a in existing):
            return False, f"Agent '{agent.display_name}' is already installed"

        custom_agent_builder.create_agent(
            name=agent.name,
            role=agent.display_name,
            system_prompt=agent.system_prompt,
            avatar=None,
            model=model,
            provider=provider,
            temperature=0.5,
            memory_enabled=True,
            allowed_tools=agent.tools or None,
        )

        logger.info("Installed marketplace agent: %s (%s)", agent.display_name, agent_id)
        return True, f"Agent '{agent.display_name}' installed successfully"

    def _map_model_tier(self, tier: str) -> Tuple[Optional[str], Optional[str]]:
        mapping = {
            "fable": ("anthropic", "claude-sonnet-4-20250514"),
            "opus": ("anthropic", "claude-sonnet-4-20250514"),
            "sonnet": ("anthropic", "claude-sonnet-4-20250514"),
            "haiku": ("anthropic", "claude-sonnet-4-20250514"),
            "inherit": (None, None),
        }
        return mapping.get(tier, (None, None))

    def get_stats(self) -> Dict[str, Any]:
        if not self._loaded:
            self.load_all()
        return {
            "total_agents": len(self._agents),
            "total_plugins": len(self._plugins),
            "categories": len(self.list_categories()),
        }


marketplace_reader = WSMarketplaceReader()