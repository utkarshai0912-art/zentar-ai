"""Database models package."""

from app.models.base import BaseModel
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.vault import (
    AuditLog,
    EnvVariable,
    Integration,
    McpServer,
    PlatformApiKey,
    UserCredential,
)

# Additional models imported for Alembic autogenerate support
__all__ = [
    "BaseModel",
    "User",
    "Conversation",
    "Message",
    "UserCredential",
    "EnvVariable",
    "Integration",
    "McpServer",
    "PlatformApiKey",
    "AuditLog",
]
