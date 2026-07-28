"""
Zentar Intelligence — Conversation & Message Models

Chat conversations with message history, supporting multi-turn AI interactions.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseModel, TenantMixin


class Conversation(BaseModel, TenantMixin, Base):
    """A chat conversation containing multiple messages."""

    __tablename__ = "conversations"

    title: str = Column(String(255), default="New Conversation")
    model_id: str = Column(String(100), nullable=True)
    provider: str = Column(String(50), nullable=True)
    system_prompt: str = Column(Text, nullable=True)
    metadata: dict = Column(JSONB, default=dict)

    # Settings
    temperature: float = Column(..., default=0.7)  # type: ignore
    max_tokens: int = Column(Integer, default=4096)
    top_p: float = Column(..., default=1.0)  # type: ignore
    stream: bool = Column(..., default=True)  # type: ignore

    # Status
    is_archived: bool = Column(..., default=False)  # type: ignore
    is_pinned: bool = Column(..., default=False)  # type: ignore
    message_count: int = Column(Integer, default=0)

    # Folder / project association
    folder_id: str = Column(String(36), nullable=True)
    project_id: str = Column(String(36), nullable=True)

    # Relationships
    messages = relationship(
        "Message",
        back_populates="conversation",
        lazy="selectin",
        order_by="Message.created_at",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, title={self.title[:50]})>"


class Message(BaseModel, Base):
    """A single message within a conversation."""

    __tablename__ = "messages"

    conversation_id: str = Column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: str = Column(String(20), nullable=False)  # user, assistant, system, tool
    content: str = Column(Text, nullable=False)
    content_type: str = Column(String(50), default="text")  # text, code, image, file

    # Token tracking
    input_tokens: int = Column(Integer, default=0)
    output_tokens: int = Column(Integer, default=0)
    total_tokens: int = Column(Integer, default=0)

    # For streaming / state
    status: str = Column(String(20), default="completed")  # streaming, completed, error
    error_message: str = Column(Text, nullable=True)

    # AI provider info
    provider: str = Column(String(50), nullable=True)
    model: str = Column(String(100), nullable=True)

    # Attachments / tool calls
    attachments: dict = Column(JSONB, default=list)
    tool_calls: dict = Column(JSONB, default=list)
    tool_results: dict = Column(JSONB, default=list)
    metadata: dict = Column(JSONB, default=dict)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, role={self.role}, conv={self.conversation_id})>"
