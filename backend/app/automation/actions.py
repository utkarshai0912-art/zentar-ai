"""
Zentar Intelligence — Automation Actions

Pre-defined action types for the automation engine.
"""

import logging
from typing import Any, Callable, Dict, Optional

from app.automation.engine import AutomationAction

logger = logging.getLogger("zentar.automation.actions")


def create_http_action(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
    action_id: Optional[str] = None,
) -> AutomationAction:
    """Create an HTTP request action."""
    import aiohttp

    async def handler(**kwargs):
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.request(method, url, json=body) as resp:
                return {
                    "status": resp.status,
                    "body": await resp.text(),
                }

    return AutomationAction(
        action_id=action_id or f"http_{id}",
        action_type="http_request",
        config={"url": url, "method": method},
        handler=handler,
    )


def create_notification_action(
    title: str,
    content: str,
    action_id: Optional[str] = None,
) -> AutomationAction:
    """Create a local notification action."""
    async def handler(**kwargs):
        logger.info("Notification: %s - %s", title, content)
        return {"sent": True, "title": title}

    return AutomationAction(
        action_id=action_id or f"notif_action_{int(time.time())}",
        action_type="notification",
        config={"title": title, "content": content},
        handler=handler,
    )


def create_delay_action(
    seconds: int,
    action_id: Optional[str] = None,
) -> AutomationAction:
    """Create a delay/wait action."""
    import asyncio

    async def handler(**kwargs):
        await asyncio.sleep(seconds)
        return {"delayed": seconds}

    return AutomationAction(
        action_id=action_id or f"delay_{seconds}s",
        action_type="delay",
        config={"seconds": seconds},
        handler=handler,
    )


def create_ai_action(
    prompt: str,
    provider: Optional[str] = None,
    action_id: Optional[str] = None,
) -> AutomationAction:
    """Create an AI prompt action."""
    from app.services.ai_service import provider_registry

    async def handler(**kwargs):
        result = []
        async for event in provider_registry.route_request(
            messages=[{"role": "user", "content": prompt.format(**kwargs)}],
            provider_name=provider,
            stream=False,
        ):
            if event["type"] == "done":
                result.append(event.get("content", ""))
        return {"result": "".join(result)}

    return AutomationAction(
        action_id=action_id or f"ai_action_{int(time.time())}",
        action_type="ai_prompt",
        config={"prompt": prompt, "provider": provider},
        handler=handler,
    )


def create_condition_action(
    condition_key: str,
    expected_value: Any,
    then_actions: list,
    else_actions: Optional[list] = None,
    action_id: Optional[str] = None,
) -> AutomationAction:
    """Create a conditional branching action."""
    async def handler(**kwargs):
        actual = kwargs.get(condition_key)
        if actual == expected_value:
            for action in then_actions:
                await action.execute(kwargs)
            return {"branch": "then"}
        elif else_actions:
            for action in else_actions:
                await action.execute(kwargs)
            return {"branch": "else"}
        return {"branch": "none"}

    return AutomationAction(
        action_id=action_id or f"cond_{int(time.time())}",
        action_type="condition",
        config={"key": condition_key, "expected": expected_value},
        handler=handler,
    )
