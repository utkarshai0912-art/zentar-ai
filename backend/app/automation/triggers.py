"""
Zentar Intelligence — Automation Triggers

Pre-defined trigger types for the automation engine.
"""

import time
from typing import Any, Callable, Dict, Optional

from app.automation.engine import AutomationTrigger
from app.services.ai_service import provider_registry


def create_schedule_trigger(
    cron_expression: str,
    trigger_id: Optional[str] = None,
) -> AutomationTrigger:
    """Create a time-based schedule trigger.

    Args:
        cron_expression: Simple format "every_X_seconds" or "daily_HH:MM"
    """
    import random
    return AutomationTrigger(
        trigger_id=trigger_id or f"schedule_{int(time.time())}",
        trigger_type="schedule",
        config={
            "cron": cron_expression,
            "type": "cron" if " " in cron_expression else "interval",
        },
    )


def create_app_trigger(
    app_package: str,
    event: str = "opened",
    trigger_id: Optional[str] = None,
) -> AutomationTrigger:
    """Create a trigger that fires when an app event occurs.

    Args:
        app_package: Android app package name
        event: opened, closed, notification, foreground
    """
    return AutomationTrigger(
        trigger_id=trigger_id or f"app_{app_package}_{event}",
        trigger_type="app_event",
        config={
            "app_package": app_package,
            "event": event,
        },
    )


def create_notification_trigger(
    app_package: Optional[str] = None,
    keyword: Optional[str] = None,
    trigger_id: Optional[str] = None,
) -> AutomationTrigger:
    """Create a trigger that fires on notifications.

    Args:
        app_package: Filter by app (None = any app)
        keyword: Filter by keyword in notification text
    """
    config = {}
    if app_package:
        config["app_package"] = app_package
    if keyword:
        config["keyword"] = keyword

    return AutomationTrigger(
        trigger_id=trigger_id or f"notif_{int(time.time())}",
        trigger_type="notification",
        config=config,
    )


def create_time_trigger(
    hour: int,
    minute: int,
    days: Optional[list] = None,
    trigger_id: Optional[str] = None,
) -> AutomationTrigger:
    """Create a trigger that fires at a specific time.

    Args:
        hour: Hour (0-23)
        minute: Minute (0-59)
        days: Days of week (0=Monday, 6=Sunday, None=daily)
    """
    config = {"hour": hour, "minute": minute}
    if days:
        config["days"] = days

    return AutomationTrigger(
        trigger_id=trigger_id or f"time_{hour:02d}{minute:02d}",
        trigger_type="time",
        config=config,
    )


def create_webhook_trigger(
    webhook_path: str,
    method: str = "POST",
    trigger_id: Optional[str] = None,
) -> AutomationTrigger:
    """Create a trigger that fires on webhook call."""
    return AutomationTrigger(
        trigger_id=trigger_id or f"webhook_{webhook_path}",
        trigger_type="webhook",
        config={
            "path": webhook_path,
            "method": method,
        },
    )
