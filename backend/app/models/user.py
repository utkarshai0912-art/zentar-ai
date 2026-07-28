"""
Zentar Intelligence — User Model

User accounts with authentication, profile, and preferences.
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseModel


class User(BaseModel, Base):
    """User account model."""

    __tablename__ = "users"

    # Authentication
    email: str = Column(String(255), unique=True, nullable=False, index=True)
    email_verified: bool = Column(Boolean, default=False, nullable=False)
    password_hash: str = Column(String(255), nullable=True)
    auth_provider: str = Column(String(50), default="local", nullable=False)
    auth_provider_id: str = Column(String(255), nullable=True)

    # Profile
    display_name: str = Column(String(100), nullable=False)
    avatar_url: str = Column(Text, nullable=True)
    bio: str = Column(Text, nullable=True)
    timezone: str = Column(String(50), default="UTC")

    # Roles & Permissions
    role: str = Column(String(50), default="user", nullable=False)  # user, admin, developer
    permissions: list = Column(ARRAY(String), default=["read", "write"], nullable=False)
    is_active: bool = Column(Boolean, default=True, nullable=False)
    is_superuser: bool = Column(Boolean, default=False, nullable=False)

    # Preferences
    theme: str = Column(String(20), default="system", nullable=False)
    language: str = Column(String(10), default="en", nullable=False)
    preferences: dict = Column(JSONB, default=dict, nullable=False)

    # Usage
    total_conversations: int = Column(Integer, default=0)
    total_messages: int = Column(Integer, default=0)
    total_tokens_used: int = Column(Integer, default=0)

    # Security
    last_login_at: DateTime = Column(DateTime(timezone=True), nullable=True)
    last_login_ip: str = Column(String(45), nullable=True)
    failed_login_attempts: int = Column(Integer, default=0)
    locked_until: DateTime = Column(DateTime(timezone=True), nullable=True)

    # API
    api_key: str = Column(String(100), unique=True, nullable=True)
    api_key_created_at: DateTime = Column(DateTime(timezone=True), nullable=True)

    # Relationships (defined as strings to avoid circular imports)
    conversations = relationship(
        "Conversation", back_populates="user", lazy="selectin"
    )
    api_keys = relationship("ApiKey", back_populates="user", lazy="selectin")
    sessions = relationship("Session", back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
