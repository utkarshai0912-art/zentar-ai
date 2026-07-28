"""
Zentar Intelligence — Plugin Manager

Lifecycle management for plugins: install, enable, disable, uninstall,
and configuration management.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

from app.core.config import get_settings
from app.plugins.registry import PluginMetadata, PluginRegistry, plugin_registry
from app.plugins.sandbox import PluginSandbox

logger = logging.getLogger("zentar.plugins.manager")

settings = get_settings()


class PluginManager:
    """Manages plugin lifecycle — install, enable, disable, uninstall."""

    def __init__(self):
        self._sandboxes: Dict[str, PluginSandbox] = {}
        self._configs: Dict[str, Dict[str, Any]] = {}
        self._plugin_sources: Dict[str, str] = {}  # plugin_id -> source path

    async def install(
        self,
        plugin_id: str,
        source: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Install a plugin from the registry."""
        plugin = plugin_registry.get(plugin_id)
        if not plugin:
            logger.error("Plugin %s not found in registry", plugin_id)
            return False

        if plugin.is_installed:
            logger.warning("Plugin %s is already installed", plugin_id)
            return False

        # Check dependencies
        for dep in plugin.dependencies:
            dep_plugin = plugin_registry.get(dep)
            if not dep_plugin or not dep_plugin.is_installed:
                logger.error("Missing dependency %s for plugin %s", dep, plugin_id)
                return False

        # Create sandbox
        sandbox = PluginSandbox(
            plugin_id=plugin_id,
            permissions=plugin.permissions,
            workspace_path=source,
        )
        self._sandboxes[plugin_id] = sandbox
        self._plugin_sources[plugin_id] = source or ""

        plugin.is_installed = True
        plugin.installed_at = time.time()

        if config:
            self._configs[plugin_id] = config
            plugin.is_enabled = True

        logger.info("Installed plugin: %s v%s", plugin.name, plugin.version)
        return True

    async def uninstall(self, plugin_id: str) -> bool:
        """Uninstall a plugin."""
        plugin = plugin_registry.get(plugin_id)
        if not plugin or not plugin.is_installed:
            return False

        # Check if other plugins depend on this one
        for other in plugin_registry.list_plugins(installed_only=True):
            if other.plugin_id != plugin_id and plugin_id in other.dependencies:
                logger.error("Cannot uninstall %s: required by %s", plugin_id, other.plugin_id)
                return False

        # Disable first
        if plugin.is_enabled:
            await self.disable(plugin_id)

        plugin.is_installed = False
        plugin.installed_at = None
        plugin.is_enabled = False

        self._sandboxes.pop(plugin_id, None)
        self._configs.pop(plugin_id, None)
        self._plugin_sources.pop(plugin_id, None)

        logger.info("Uninstalled plugin: %s", plugin.name)
        return True

    async def enable(self, plugin_id: str, config: Optional[Dict] = None) -> bool:
        """Enable an installed plugin."""
        plugin = plugin_registry.get(plugin_id)
        if not plugin or not plugin.is_installed:
            return False

        if config:
            self._configs[plugin_id] = config

        plugin.is_enabled = True
        logger.info("Enabled plugin: %s", plugin.name)
        return True

    async def disable(self, plugin_id: str) -> bool:
        """Disable an enabled plugin."""
        plugin = plugin_registry.get(plugin_id)
        if not plugin or not plugin.is_enabled:
            return False

        plugin.is_enabled = False
        logger.info("Disabled plugin: %s", plugin.name)
        return True

    def get_config(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        """Get plugin configuration."""
        return self._configs.get(plugin_id)

    def update_config(self, plugin_id: str, config: Dict[str, Any]) -> bool:
        """Update plugin configuration."""
        if plugin_id not in self._configs:
            return False
        self._configs[plugin_id].update(config)
        return True

    def get_sandbox(self, plugin_id: str) -> Optional[PluginSandbox]:
        """Get the sandbox for a plugin."""
        return self._sandboxes.get(plugin_id)

    def list_plugins(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """List all plugins with installation status."""
        plugins = plugin_registry.list_plugins(enabled_only=enabled_only, installed_only=True)
        result = []
        for p in plugins:
            info = p.to_dict()
            info["config"] = self._configs.get(p.plugin_id)
            info["sandbox"] = self._sandboxes.get(p.plugin_id, {}).to_dict() if p.plugin_id in self._sandboxes else None
            result.append(info)
        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get plugin manager statistics."""
        installed = [p for p in plugin_registry.list_plugins() if p.is_installed]
        enabled = [p for p in installed if p.is_enabled]
        return {
            "total": plugin_registry.count(),
            "installed": len(installed),
            "enabled": len(enabled),
            "sandboxes_active": len(self._sandboxes),
        }


# Global plugin manager
plugin_manager = PluginManager()
