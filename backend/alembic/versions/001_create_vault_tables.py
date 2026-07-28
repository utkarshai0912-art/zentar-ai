"""Create vault tables for user secrets, integrations, MCP servers, audit logs

Revision ID: 001_create_vault_tables
Revises:
Create Date: 2026-07-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "001_create_vault_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # UserCredentials
    op.create_table(
        "user_credentials",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()), index=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("provider_name", sa.String(50), nullable=False, index=True),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("api_key_encrypted", sa.Text, nullable=False),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("org_id", sa.String(255), nullable=True),
        sa.Column("project_id", sa.String(255), nullable=True),
        sa.Column("default_model", sa.String(100), nullable=True),
        sa.Column("max_tokens", sa.Integer, nullable=True),
        sa.Column("temperature", sa.Float, nullable=True),
        sa.Column("timeout", sa.Integer, default=30),
        sa.Column("is_enabled", sa.Boolean, default=True, nullable=False),
        sa.Column("is_default", sa.Boolean, default=False, nullable=False),
        sa.Column("priority", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), default=sa.func.now(), nullable=False, index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean, default=False, nullable=False, index=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # EnvVariables
    op.create_table(
        "env_variables",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()), index=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("value_encrypted", sa.Text, nullable=False),
        sa.Column("category", sa.String(50), default="general"),
        sa.Column("is_sensitive", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), default=sa.func.now(), nullable=False, index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean, default=False, nullable=False, index=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Integrations
    op.create_table(
        "integrations",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()), index=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("integration_type", sa.String(50), nullable=False, index=True),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("credentials_encrypted", sa.Text, nullable=True),
        sa.Column("is_enabled", sa.Boolean, default=True, nullable=False),
        sa.Column("health_status", sa.String(20), default="unknown"),
        sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), default=sa.func.now(), nullable=False, index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean, default=False, nullable=False, index=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # McpServers
    op.create_table(
        "mcp_servers",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()), index=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("server_url", sa.String(500), nullable=False),
        sa.Column("auth_type", sa.String(20), default="none"),
        sa.Column("auth_config_encrypted", sa.Text, nullable=True),
        sa.Column("permissions", JSONB, default=list),
        sa.Column("allowed_agents", JSONB, default=list),
        sa.Column("is_enabled", sa.Boolean, default=True, nullable=False),
        sa.Column("health_status", sa.String(20), default="unknown"),
        sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auto_reconnect", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), default=sa.func.now(), nullable=False, index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean, default=False, nullable=False, index=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # PlatformApiKeys
    op.create_table(
        "platform_api_keys",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()), index=True),
        sa.Column("provider_name", sa.String(50), unique=True, nullable=False, index=True),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("api_key_encrypted", sa.Text, nullable=False),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("org_id", sa.String(255), nullable=True),
        sa.Column("default_model", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean, default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), default=sa.func.now(), nullable=False, index=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean, default=False, nullable=False, index=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # AuditLogs
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()), index=True),
        sa.Column("user_id", sa.String(36), nullable=True, index=True),
        sa.Column("action", sa.String(50), nullable=False, index=True),
        sa.Column("resource_type", sa.String(50), nullable=False, index=True),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("details", JSONB, default=dict),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), default=sa.func.now(), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("platform_api_keys")
    op.drop_table("mcp_servers")
    op.drop_table("integrations")
    op.drop_table("env_variables")
    op.drop_table("user_credentials")