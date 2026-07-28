"""
Zentar Intelligence — Plugin Registry

Registry for discovering and managing installed plugins.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("zentar.plugins.registry")


class PluginMetadata:
    """Metadata for an installed plugin."""

    def __init__(
        self,
        plugin_id: str,
        name: str,
        version: str,
        author: str,
        description: str,
        permissions: List[str],
        dependencies: Optional[List[str]] = None,
        config_schema: Optional[Dict[str, Any]] = None,
        homepage: Optional[str] = None,
        license: Optional[str] = None,
        icon: Optional[str] = None,
    ):
        self.plugin_id = plugin_id
        self.name = name
        self.version = version
        self.author = author
        self.description = description
        self.permissions = permissions
        self.dependencies = dependencies or []
        self.config_schema = config_schema or {}
        self.homepage = homepage
        self.license = license
        self.icon = icon
        self.is_enabled = False
        self.is_installed = False
        self.installed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "permissions": self.permissions,
            "dependencies": self.dependencies,
            "is_enabled": self.is_enabled,
            "is_installed": self.is_installed,
            "homepage": self.homepage,
            "license": self.license,
            "icon": self.icon,
        }


class PluginRegistry:
    """Registry for plugin metadata and discovery."""

    def __init__(self):
        self._plugins: Dict[str, PluginMetadata] = {}
        self._categories: Dict[str, List[str]] = {}

    def register(self, plugin: PluginMetadata, category: str = "uncategorized"):
        """Register a plugin in the registry."""
        self._plugins[plugin.plugin_id] = plugin
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(plugin.plugin_id)
        logger.info("Registered plugin: %s v%s (%s)", plugin.name, plugin.version, category)

    def unregister(self, plugin_id: str):
        """Unregister a plugin."""
        plugin = self._plugins.pop(plugin_id, None)
        if plugin:
            for cat in self._categories.values():
                if plugin_id in cat:
                    cat.remove(plugin_id)

    def get(self, plugin_id: str) -> Optional[PluginMetadata]:
        """Get plugin metadata by ID."""
        return self._plugins.get(plugin_id)

    def get_by_name(self, name: str) -> Optional[PluginMetadata]:
        """Find a plugin by name."""
        for plugin in self._plugins.values():
            if plugin.name == name:
                return plugin
        return None

    def list_plugins(
        self,
        category: Optional[str] = None,
        enabled_only: bool = False,
        installed_only: bool = False,
    ) -> List[PluginMetadata]:
        """List plugins with optional filters."""
        plugins = list(self._plugins.values())

        if category:
            names = self._categories.get(category, [])
            plugins = [p for p in plugins if p.plugin_id in names]

        if enabled_only:
            plugins = [p for p in plugins if p.is_enabled]

        if installed_only:
            plugins = [p for p in plugins if p.is_installed]

        return plugins

    def list_categories(self) -> List[str]:
        """List all plugin categories."""
        return list(self._categories.keys())

    def count(self) -> int:
        """Total number of registered plugins."""
        return len(self._plugins)


# Global plugin registry
plugin_registry = PluginRegistry()
