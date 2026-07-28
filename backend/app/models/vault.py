"""
Zentar Intelligence — User Secrets Vault Models

Database models for user-managed credentials, environment variables,
third-party integrations, MCP servers, and audit logging.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import BaseModel, TenantMixin


class UserCredential(BaseModel, TenantMixin, Base):
    """User-owned AI provider API credentials."""

    __tablename__ = "user_credentials"

    provider_name: str = Column(String(50), nullable=False, index=True)
    label: str = Column(String(100), nullable=False)
    api_key_encrypted: str = Column(Text, nullable=False)
    base_url: str = Column(String(500), nullable=True)
    org_id: str = Column(String(255), nullable=True)
    project_id: str = Column(String(255), nullable=True)
    default_model: str = Column(String(100), nullable=True)
    max_tokens: int = Column(Integer, nullable=True)
    temperature: float = Column(Float, nullable=True)
    timeout: int = Column(Integer, default=30)

    is_enabled: bool = Column(Boolean, default=True, nullable=False)
    is_default: bool = Column(Boolean, default=False, nullable=False)
    priority: int = Column(Integer, default=0)

    user_id: str = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user = relationship("User", backref="credentials")

    def __repr__(self):
        return f"<UserCredential(id={self.id}, provider={self.provider_name}, user={self.user_id})>"


class EnvVariable(BaseModel, TenantMixin, Base):
    """User-defined environment variables."""

    __tablename__ = "env_variables"

    name: str = Column(String(255), nullable=False)
    value_encrypted: str = Column(Text, nullable=False)
    category: str = Column(String(50), default="general")
    is_sensitive: bool = Column(Boolean, default=True)

    user_id: str = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user = relationship("User", backref="env_variables")

    def __repr__(self):
        return f"<EnvVariable(id={self.id}, name={self.name}, user={self.user_id})>"


class Integration(BaseModel, TenantMixin, Base):
    """Third-party service integrations."""

    __tablename__ = "integrations"

    integration_type: str = Column(String(50), nullable=False, index=True)
    label: str = Column(String(100), nullable=False)
    credentials_encrypted: str = Column(Text, nullable=True)

    is_enabled: bool = Column(Boolean, default=True, nullable=False)
    health_status: str = Column(String(20), default="unknown")
    last_health_check_at: DateTime = Column(DateTime(timezone=True), nullable=True)

    user_id: str = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user = relationship("User", backref="integrations")

    def __repr__(self):
        return f"<Integration(id={self.id}, type={self.integration_type}, user={self.user_id})>"


class McpServer(BaseModel, TenantMixin, Base):
    """User-registered MCP servers."""

    __tablename__ = "mcp_servers"

    name: str = Column(String(100), nullable=False)
    description: str = Column(Text, nullable=True)
    server_url: str = Column(String(500), nullable=False)
    auth_type: str = Column(String(20), default="none")
    auth_config_encrypted: str = Column(Text, nullable=True)
    permissions: list = Column(JSONB, default=list)
    allowed_agents: list = Column(JSONB, default=list)

    is_enabled: bool = Column(Boolean, default=True, nullable=False)
    health_status: str = Column(String(20), default="unknown")
    last_health_check_at: DateTime = Column(DateTime(timezone=True), nullable=True)
    auto_reconnect: bool = Column(Boolean, default=False)

    user_id: str = Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user = relationship("User", backref="mcp_servers")

    def __repr__(self):
        return f"<McpServer(id={self.id}, name={self.name}, user={self.user_id})>"


class PlatformApiKey(BaseModel, Base):
    """Admin-managed platform API keys (no tenant)."""

    __tablename__ = "platform_api_keys"

    provider_name: str = Column(String(50), unique=True, nullable=False, index=True)
    label: str = Column(String(100), nullable=False)
    api_key_encrypted: str = Column(Text, nullable=False)
    base_url: str = Column(String(500), nullable=True)
    org_id: str = Column(String(255), nullable=True)
    default_model: str = Column(String(100), nullable=True)
    is_active: bool = Column(Boolean, default=True, nullable=False)

    def __repr__(self):
        return f"<PlatformApiKey(id={self.id}, provider={self.provider_name})>"


class AuditLog(BaseModel, Base):
    """Audit trail for credential and configuration changes."""

    __tablename__ = "audit_logs"

    user_id: str = Column(String(36), nullable=True, index=True)
    action: str = Column(String(50), nullable=False, index=True)
    resource_type: str = Column(String(50), nullable=False, index=True)
    resource_id: str = Column(String(36), nullable=True)
    details: dict = Column(JSONB, default=dict)
    ip_address: str = Column(String(45), nullable=True)

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, resource={self.resource_type})>"