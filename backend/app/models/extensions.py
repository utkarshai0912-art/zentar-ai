"""
Zentar Intelligence — API Key, Session, Plugin, Skill & Memory Models
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseModel, TenantMixin


class ApiKey(BaseModel, TenantMixin, Base):
    """API keys for programmatic access."""

    __tablename__ = "api_keys"

    name: str = Column(String(100), nullable=False)
    key_hash: str = Column(String(255), nullable=False, unique=True)
    key_prefix: str = Column(String(20), nullable=False)  # First chars for identification
    permissions: list = Column(JSONB, default=list)
    rate_limit: int = Column(Integer, default=1000)
    last_used_at: DateTime = Column(DateTime(timezone=True), nullable=True)
    expires_at: DateTime = Column(DateTime(timezone=True), nullable=True)

    user_id: str = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<ApiKey(id={self.id}, name={self.name}, prefix={self.key_prefix})>"


class Session(BaseModel, TenantMixin, Base):
    """User session tracking."""

    __tablename__ = "sessions"

    token_jti: str = Column(String(100), unique=True, nullable=False, index=True)
    token_type: str = Column(String(20), nullable=False)  # access, refresh
    device_info: dict = Column(JSONB, default=dict)
    ip_address: str = Column(String(45), nullable=True)
    user_agent: str = Column(Text, nullable=True)
    expires_at: DateTime = Column(DateTime(timezone=True), nullable=False)
    is_revoked: bool = Column(Boolean, default=False, nullable=False)
    revoked_at: DateTime = Column(DateTime(timezone=True), nullable=True)

    user_id: str = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<Session(id={self.id}, type={self.token_type}, user={self.user_id})>"


class Plugin(BaseModel, Base):
    """Plugin registry — installed plugins and their metadata."""

    __tablename__ = "plugins"

    name: str = Column(String(100), unique=True, nullable=False)
    display_name: str = Column(String(255), nullable=False)
    description: str = Column(Text, nullable=True)
    version: str = Column(String(20), nullable=False)
    author: str = Column(String(100), nullable=True)
    homepage: str = Column(String(500), nullable=True)
    license_type: str = Column(String(50), nullable=True)

    # Installation
    source_url: str = Column(Text, nullable=True)
    install_type: str = Column(String(20), default="marketplace")  # marketplace, url, local
    checksum: str = Column(String(64), nullable=True)

    # Permissions
    permissions: list = Column(JSONB, default=list)

    # Status
    is_enabled: bool = Column(Boolean, default=True, nullable=False)
    is_official: bool = Column(Boolean, default=False, nullable=False)
    is_sandboxed: bool = Column(Boolean, default=True, nullable=False)

    # Configuration
    config_schema: dict = Column(JSONB, default=dict)
    config: dict = Column(JSONB, default=dict)

    # Lifecycle
    installed_at: DateTime = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: DateTime = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    # Dependencies
    dependencies: list = Column(JSONB, default=list)

    def __repr__(self):
        return f"<Plugin(id={self.id}, name={self.name}, v{self.version})>"


class Skill(BaseModel, Base):
    """AI skill definitions — reusable capability packages."""

    __tablename__ = "skills"

    name: str = Column(String(100), unique=True, nullable=False)
    display_name: str = Column(String(255), nullable=False)
    description: str = Column(Text, nullable=True)
    version: str = Column(String(20), nullable=False)
    author: str = Column(String(100), nullable=True)
    category: str = Column(String(50), default="general")  # coding, security, marketing, etc.
    tags: list = Column(JSONB, default=list)

    # Core
    system_prompt: str = Column(Text, nullable=False)
    tools: list = Column(JSONB, default=list)
    memory_rules: list = Column(JSONB, default=list)

    # Permissions
    permissions: list = Column(JSONB, default=list)

    # Provider / model
    preferred_provider: str = Column(String(50), nullable=True)
    preferred_model: str = Column(String(100), nullable=True)

    # Status
    is_enabled: bool = Column(Boolean, default=True, nullable=False)
    is_official: bool = Column(Boolean, default=False, nullable=False)

    # Configuration
    config_schema: dict = Column(JSONB, default=dict)
    config: dict = Column(JSONB, default=dict)

    # Dependencies
    dependencies: list = Column(JSONB, default=list)
    required_plugins: list = Column(JSONB, default=list)

    # Installation
    source_url: str = Column(Text, nullable=True)
    install_type: str = Column(String(20), default="marketplace")

    def __repr__(self):
        return f"<Skill(id={self.id}, name={self.name}, v{self.version})>"


class Memory(BaseModel, TenantMixin, Base):
    """Memory entries for long-term and project-scoped recall."""

    __tablename__ = "memories"

    content: str = Column(Text, nullable=False)
    memory_type: str = Column(String(20), default="conversation")  # conversation, long_term, project, pinned, note
    scope: str = Column(String(20), default="user")  # user, project, global

    # Embedding
    embedding: list = Column(JSONB, nullable=True)
    embedding_model: str = Column(String(100), nullable=True)

    # Metadata
    source: str = Column(String(50), nullable=True)  # chat, import, manual
    importance: int = Column(Integer, default=0)  # 0-10
    tags: list = Column(JSONB, default=list)
    context: dict = Column(JSONB, default=dict)

    # Project association
    project_id: str = Column(String(36), nullable=True, index=True)
    conversation_id: str = Column(String(36), nullable=True)

    # For memory decay
    last_recalled_at: DateTime = Column(DateTime(timezone=True), nullable=True)
    recall_count: int = Column(Integer, default=0)

    def __repr__(self):
        return f"<Memory(id={self.id}, type={self.memory_type}, user={self.user_id})>"
