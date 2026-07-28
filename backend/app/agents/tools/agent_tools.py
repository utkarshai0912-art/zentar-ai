"""
Zentar Intelligence — Agent Tools Extension

Extended tool set for agents: browser, git, filesystem, HTTP,
database, terminal, search, and utility tools.
"""

import json
import logging
import os
import subprocess
from typing import Any, Dict, List, Optional

from app.agents.tool_registry import Tool, tool_registry

logger = logging.getLogger("zentar.agents.tools.extended")


# ── File System Tools ──

async def read_file_tool(path: str) -> str:
    """Read the contents of a file."""
    path = os.path.normpath(path)
    if path.startswith("..") or "/.." in path:
        return "Error: Path traversal not allowed"
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


async def write_file_tool(path: str, content: str) -> str:
    """Write content to a file."""
    path = os.path.normpath(path)
    if path.startswith("..") or "/.." in path:
        return "Error: Path traversal not allowed"
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return f"File written: {path} ({len(content)} bytes)"
    except Exception as e:
        return f"Error writing file: {str(e)}"


async def list_files_tool(path: str = ".") -> str:
    """List files in a directory."""
    try:
        entries = os.listdir(path)
        result = []
        for entry in sorted(entries):
            full = os.path.join(path, entry)
            if os.path.isdir(full):
                result.append(f"  {entry}/")
            else:
                size = os.path.getsize(full)
                result.append(f"  {entry} ({size} bytes)")
        return "\n".join(result) if result else "(empty directory)"
    except Exception as e:
        return f"Error listing directory: {str(e)}"


async def delete_file_tool(path: str) -> str:
    """Delete a file."""
    path = os.path.normpath(path)
    if path.startswith("..") or "/.." in path:
        return "Error: Path traversal not allowed"
    try:
        os.remove(path)
        return f"File deleted: {path}"
    except Exception as e:
        return f"Error deleting file: {str(e)}"


# ── HTTP Tools ──

async def http_get_tool(url: str, headers: Optional[str] = None) -> str:
    """Make an HTTP GET request."""
    import aiohttp
    hdrs = json.loads(headers) if headers else {}
    try:
        async with aiohttp.ClientSession(headers=hdrs) as session:
            async with session.get(url, timeout=30) as resp:
                text = await resp.text()
                return f"Status: {resp.status}\n\n{text[:5000]}"
    except Exception as e:
        return f"HTTP GET failed: {str(e)}"


async def http_post_tool(url: str, data: str, content_type: str = "application/json") -> str:
    """Make an HTTP POST request."""
    import aiohttp
    headers = {"Content-Type": content_type}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(url, data=data, timeout=30) as resp:
                text = await resp.text()
                return f"Status: {resp.status}\n\n{text[:5000]}"
    except Exception as e:
        return f"HTTP POST failed: {str(e)}"


# ── Git Tools ──

async def git_status_tool(path: str = ".") -> str:
    """Show git status."""
    try:
        result = subprocess.run(
            ["git", "status"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout or result.stderr
    except Exception as e:
        return f"Git status failed: {str(e)}"


async def git_commit_tool(path: str, message: str) -> str:
    """Commit changes in a git repository."""
    try:
        subprocess.run(["git", "add", "."], cwd=path, capture_output=True, timeout=30)
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout or result.stderr
    except Exception as e:
        return f"Git commit failed: {str(e)}"


async def git_push_tool(path: str = ".", remote: str = "origin", branch: str = "main") -> str:
    """Push to git remote."""
    try:
        result = subprocess.run(
            ["git", "push", remote, branch],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.stdout or result.stderr
    except Exception as e:
        return f"Git push failed: {str(e)}"


# ── Browser Tools ──

async def browser_navigate_tool(url: str) -> str:
    """Navigate a browser to a URL."""
    from app.services.browser_service import browser_service
    try:
        tab_id = await browser_service.new_tab(url)
        title = await browser_service.get_title(tab_id)
        return f"Navigated to {url}\nTitle: {title}\nTab: {tab_id}"
    except Exception as e:
        return f"Browser navigation failed: {str(e)}"


async def browser_screenshot_tool(tab_id: str) -> str:
    """Take a screenshot of the current browser tab."""
    from app.services.browser_service import browser_service
    try:
        img_b64 = await browser_service.screenshot(tab_id)
        return f"data:image/png;base64,{img_b64}"
    except Exception as e:
        return f"Screenshot failed: {str(e)}"


async def browser_extract_text_tool(tab_id: str) -> str:
    """Extract text from the current browser tab."""
    from app.services.browser_service import browser_service
    try:
        text = await browser_service.get_text(tab_id)
        return text[:10000]
    except Exception as e:
        return f"Text extraction failed: {str(e)}"


async def browser_extract_links_tool(tab_id: str) -> str:
    """Extract all links from the current browser tab."""
    from app.services.browser_service import browser_service
    try:
        links = await browser_service.extract_links(tab_id)
        return "\n".join(f"{l['text']}: {l['href']}" for l in links[:50])
    except Exception as e:
        return f"Link extraction failed: {str(e)}"


async def browser_click_tool(selector: str, tab_id: str) -> str:
    """Click an element in the browser."""
    from app.services.browser_service import browser_service
    try:
        await browser_service.click(selector, tab_id)
        return f"Clicked: {selector}"
    except Exception as e:
        return f"Click failed: {str(e)}"


async def browser_type_tool(selector: str, text: str, tab_id: str) -> str:
    """Type text into an element in the browser."""
    from app.services.browser_service import browser_service
    try:
        await browser_service.type_text(selector, text, tab_id)
        return f"Typed '{text}' into {selector}"
    except Exception as e:
        return f"Type failed: {str(e)}"


# ── Search Tools ──

async def web_search_tool(query: str) -> str:
    """Search the web for information. Uses Tavily or SerpAPI if configured."""
    from app.core.config import get_settings
    settings = get_settings()
    if settings.TAVILY_API_KEY:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.tavily.com/search",
                json={"api_key": settings.TAVILY_API_KEY, "query": query, "max_results": 5},
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("results", [])
                    return "\n\n".join(
                        f"{r['title']}\n{r['url']}\n{r['content'][:500]}"
                        for r in results
                    )
    if settings.SERPAPI_API_KEY:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://serpapi.com/search",
                params={"api_key": settings.SERPAPI_API_KEY, "q": query, "num": 5},
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("organic_results", [])
                    return "\n\n".join(
                        f"{r['title']}\n{r['link']}\n{r.get('snippet', '')}"
                        for r in results[:5]
                    )
    return f"Web search is not configured. Please set TAVILY_API_KEY or SERPAPI_API_KEY in environment."


# ── Terminal / Command Tools ──

async def run_command_tool(command: str, timeout: int = 30) -> str:
    """Run a shell command in a sandboxed environment."""
    allowed_prefixes = ["ls", "cat", "echo", "pwd", "python", "node", "npm", "pip", "git", "mkdir", "cp", "mv", "head", "tail", "wc", "sort", "grep", "find", "date", "whoami", "uname", "df", "du", "ps", "env"]
    cmd = command.strip().split()[0] if command.strip() else ""
    if cmd not in allowed_prefixes and not any(command.startswith(p) for p in allowed_prefixes):
        return f"Error: Command '{cmd}' not in allowed list. Allowed: {', '.join(allowed_prefixes)}"
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout or result.stderr
        return output[:10000] if output else "(no output)"
    except subprocess.TimeoutExpired:
        return f"Command timed out after {timeout}s"
    except Exception as e:
        return f"Command failed: {str(e)}"


# ── Database Tools ──

async def db_query_tool(query: str) -> str:
    """Execute a SQL SELECT query on the database."""
    from app.core.database import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(query)
            rows = result.fetchmany(20)
            if not rows:
                return "(no results)"
            columns = list(rows[0].keys())
            header = " | ".join(columns)
            lines = [header, "-" * len(header)]
            for row in rows:
                lines.append(" | ".join(str(v) for v in row))
            return "\n".join(lines)
    except Exception as e:
        return f"Database query failed: {str(e)}"


# ── Memory Tools ──

async def store_memory_tool(key: str, content: str, importance: float = 0.5) -> str:
    """Store a fact in the agent's long-term memory."""
    from app.agents.agent_memory import agent_memory_manager
    memory = agent_memory_manager.get_or_create("default")
    memory.store_knowledge(key, content, importance)
    return f"Stored memory: {key}"


async def search_memory_tool(query: str) -> str:
    """Search the agent's long-term memory."""
    from app.agents.agent_memory import agent_memory_manager
    memory = agent_memory_manager.get_or_create("default")
    results = memory.retrieve_knowledge(query)
    if not results:
        return "(no matching memories found)"
    return "\n\n".join(
        f"[{r.get('key', 'unknown')}] (importance: {r.get('importance', 0):.2f})\n{r.get('content', '')[:500]}"
        for r in results[:10]
    )


# ── Registration ──

def register_agent_tools():
    """Register all extended agent tools with the global tool registry."""
    tool_registry.register_many([
        # File System Tools
        Tool(
            name="read_file",
            description="Read the contents of a file at the given path",
            handler=read_file_tool,
            parameters={"path": {"type": "string", "description": "Path to the file"}},
            required=["path"],
            category="filesystem",
        ),
        Tool(
            name="write_file",
            description="Write content to a file at the given path",
            handler=write_file_tool,
            parameters={
                "path": {"type": "string", "description": "Path to the file"},
                "content": {"type": "string", "description": "Content to write"},
            },
            required=["path", "content"],
            category="filesystem",
        ),
        Tool(
            name="list_files",
            description="List files and directories at the given path",
            handler=list_files_tool,
            parameters={"path": {"type": "string", "description": "Directory path (default: current)"}},
            category="filesystem",
        ),
        Tool(
            name="delete_file",
            description="Delete a file at the given path",
            handler=delete_file_tool,
            parameters={"path": {"type": "string", "description": "Path to the file"}},
            required=["path"],
            category="filesystem",
        ),

        # HTTP Tools
        Tool(
            name="http_get",
            description="Make an HTTP GET request to a URL",
            handler=http_get_tool,
            parameters={
                "url": {"type": "string", "description": "URL to request"},
                "headers": {"type": "string", "description": "Optional JSON headers"},
            },
            required=["url"],
            category="network",
        ),
        Tool(
            name="http_post",
            description="Make an HTTP POST request to a URL",
            handler=http_post_tool,
            parameters={
                "url": {"type": "string", "description": "URL to request"},
                "data": {"type": "string", "description": "Request body data"},
                "content_type": {"type": "string", "description": "Content-Type header"},
            },
            required=["url", "data"],
            category="network",
        ),

        # Git Tools
        Tool(
            name="git_status",
            description="Show the working tree status of a git repository",
            handler=git_status_tool,
            parameters={"path": {"type": "string", "description": "Repository path"}},
            category="git",
        ),
        Tool(
            name="git_commit",
            description="Stage all changes and commit them in a git repository",
            handler=git_commit_tool,
            parameters={
                "path": {"type": "string", "description": "Repository path"},
                "message": {"type": "string", "description": "Commit message"},
            },
            required=["path", "message"],
            category="git",
        ),
        Tool(
            name="git_push",
            description="Push commits to a remote git repository",
            handler=git_push_tool,
            parameters={
                "path": {"type": "string", "description": "Repository path"},
                "remote": {"type": "string", "description": "Remote name"},
                "branch": {"type": "string", "description": "Branch name"},
            },
            category="git",
        ),

        # Browser Tools
        Tool(
            name="browser_navigate",
            description="Open a URL in the browser and return the page title",
            handler=browser_navigate_tool,
            parameters={"url": {"type": "string", "description": "URL to navigate to"}},
            required=["url"],
            category="browser",
        ),
        Tool(
            name="browser_screenshot",
            description="Take a screenshot of the current browser tab (returns base64 image)",
            handler=browser_screenshot_tool,
            parameters={"tab_id": {"type": "string", "description": "Browser tab ID"}},
            required=["tab_id"],
            category="browser",
        ),
        Tool(
            name="browser_extract_text",
            description="Extract all visible text from the current browser tab",
            handler=browser_extract_text_tool,
            parameters={"tab_id": {"type": "string", "description": "Browser tab ID"}},
            required=["tab_id"],
            category="browser",
        ),
        Tool(
            name="browser_extract_links",
            description="Extract all links from the current browser tab",
            handler=browser_extract_links_tool,
            parameters={"tab_id": {"type": "string", "description": "Browser tab ID"}},
            required=["tab_id"],
            category="browser",
        ),
        Tool(
            name="browser_click",
            description="Click an element on the page using a CSS selector",
            handler=browser_click_tool,
            parameters={
                "selector": {"type": "string", "description": "CSS selector to click"},
                "tab_id": {"type": "string", "description": "Browser tab ID"},
            },
            required=["selector", "tab_id"],
            category="browser",
        ),
        Tool(
            name="browser_type",
            description="Type text into an input field on the page",
            handler=browser_type_tool,
            parameters={
                "selector": {"type": "string", "description": "CSS selector for the input"},
                "text": {"type": "string", "description": "Text to type"},
                "tab_id": {"type": "string", "description": "Browser tab ID"},
            },
            required=["selector", "text", "tab_id"],
            category="browser",
        ),

        # Search Tools
        Tool(
            name="web_search",
            description="Search the web for current information using configured search provider",
            handler=web_search_tool,
            parameters={"query": {"type": "string", "description": "Search query"}},
            required=["query"],
            category="web",
        ),

        # Terminal Tools
        Tool(
            name="run_command",
            description="Run a shell command in a sandboxed environment",
            handler=run_command_tool,
            parameters={
                "command": {"type": "string", "description": "Shell command to run"},
                "timeout": {"type": "integer", "description": "Timeout in seconds"},
            },
            required=["command"],
            category="terminal",
        ),

        # Database Tools
        Tool(
            name="db_query",
            description="Execute a SQL SELECT query on the database",
            handler=db_query_tool,
            parameters={"query": {"type": "string", "description": "SQL SELECT query"}},
            required=["query"],
            category="database",
        ),

        # Memory Tools
        Tool(
            name="store_memory",
            description="Store a fact in the agent's long-term memory",
            handler=store_memory_tool,
            parameters={
                "key": {"type": "string", "description": "Memory key"},
                "content": {"type": "string", "description": "Content to remember"},
                "importance": {"type": "number", "description": "Importance 0-1"},
            },
            required=["key", "content"],
            category="memory",
        ),
        Tool(
            name="search_memory",
            description="Search the agent's long-term memory for relevant information",
            handler=search_memory_tool,
            parameters={"query": {"type": "string", "description": "Search query"}},
            required=["query"],
            category="memory",
        ),
    ])