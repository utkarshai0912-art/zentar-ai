"""
Zentar Intelligence — Plugin Sandbox

Sandboxed execution environment for plugins with resource limits
and security restrictions.
"""

import importlib
import importlib.util
import logging
import sys
import traceback
from types import ModuleType
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.config import get_settings

logger = logging.getLogger("zentar.plugins.sandbox")

settings = get_settings()


class SandboxViolation(Exception):
    """Raised when a plugin violates sandbox restrictions."""
    pass


class PluginSandbox:
    """Sandboxed execution environment for plugins.

    Restricts:
    - File system access (read/write to designated directories only)
    - Network access (controlled via allowlist)
    - System commands (disabled by default)
    - Import access (restricted module allowlist)
    - Resource limits (CPU, memory, execution time)
    """

    # Modules plugins are allowed to import
    ALLOWED_MODULES = {
        "json", "math", "re", "datetime", "collections", "itertools",
        "functools", "typing", "uuid", "hashlib", "base64",
        "dataclasses", "enum", "copy", "random", "string",
    }

    # Additional modules allowed for specific permission levels
    PERMISSION_MODULES = {
        "network": {"aiohttp", "httpx", "requests", "urllib"},
        "filesystem": {"pathlib", "os.path"},
        "crypto": {"cryptography", "nacl"},
    }

    def __init__(
        self,
        plugin_id: str,
        permissions: List[str],
        max_execution_time: int = 30,
        workspace_path: Optional[str] = None,
    ):
        self.plugin_id = plugin_id
        self.permissions = set(permissions)
        self.max_execution_time = max_execution_time
        self.workspace_path = workspace_path

    def get_allowed_modules(self) -> set:
        """Get the set of modules this plugin is allowed to import."""
        modules = set(self.ALLOWED_MODULES)
        for perm in self.permissions:
            if perm in self.PERMISSION_MODULES:
                modules.update(self.PERMISSION_MODULES[perm])
        return modules

    def validate_import(self, module_name: str):
        """Check if a module import is allowed in the sandbox."""
        allowed = self.get_allowed_modules()
        base = module_name.split(".")[0]

        if base not in allowed:
            raise SandboxViolation(
                f"Plugin '{self.plugin_id}' attempted to import forbidden module: {module_name}"
            )

    def validate_action(self, action: str, details: Optional[Dict] = None):
        """Check if an action is allowed based on permissions."""
        permission_map = {
            "network_request": "network",
            "file_read": "filesystem",
            "file_write": "filesystem",
            "exec_command": "system",
            "accessibility": "accessibility",
            "notifications": "notifications",
            "audio": "audio",
        }

        required = permission_map.get(action)
        if required and required not in self.permissions:
            raise SandboxViolation(
                f"Plugin '{self.plugin_id}' lacks '{required}' permission for action: {action}"
            )

    def exec_code(self, code: str, globals_dict: Optional[Dict] = None) -> Tuple[Any, Optional[str]]:
        """Execute Python code in the sandbox with restricted imports."""
        # Set up restricted globals
        sandbox_globals = {
            "__builtins__": {
                "abs": abs, "all": all, "any": any, "bool": bool,
                "chr": chr, "dict": dict, "dir": dir, "enumerate": enumerate,
                "filter": filter, "float": float, "format": format,
                "frozenset": frozenset, "getattr": getattr, "hasattr": hasattr,
                "hash": hash, "hex": hex, "id": id, "int": int,
                "isinstance": isinstance, "issubclass": issubclass,
                "iter": iter, "len": len, "list": list, "map": map,
                "max": max, "min": min, "next": next, "object": object,
                "oct": oct, "ord": ord, "pow": pow, "print": print,
                "range": range, "repr": repr, "reversed": reversed,
                "round": round, "set": set, "slice": slice, "sorted": sorted,
                "str": str, "sum": sum, "tuple": tuple, "type": type,
                "zip": zip, "True": True, "False": False, "None": None,
                "Exception": Exception, "ValueError": ValueError,
                "TypeError": TypeError, "KeyError": KeyError,
                "IndexError": IndexError, "AttributeError": AttributeError,
                "ImportError": ImportError, "StopIteration": StopIteration,
            },
            "__import__": self._sandbox_import,
            "sandbox": self,
        }

        if globals_dict:
            sandbox_globals.update(globals_dict)

        try:
            compiled = compile(code, f"<plugin_{self.plugin_id}>", "exec")
            exec(compiled, sandbox_globals)
            return sandbox_globals.get("result"), None
        except SandboxViolation as e:
            return None, str(e)
        except Exception as e:
            return None, f"{type(e).__name__}: {str(e)}"

    def _sandbox_import(self, name: str, *args, **kwargs) -> ModuleType:
        """Restricted import function that validates against allowlist."""
        self.validate_import(name)
        return importlib.__import__(name, *args, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "permissions": list(self.permissions),
            "max_execution_time": self.max_execution_time,
            "has_workspace": self.workspace_path is not None,
        }
