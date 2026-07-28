"""
Zentar Intelligence — Base Database Model

Shared model mixins: UUID primary keys, timestamp columns, soft deletion.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_mixin, declared_attr


@declarative_mixin
class TimestampMixin:
    """Adds created_at and updated_at timestamp columns."""

    created_at: datetime = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at: datetime = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


@declarative_mixin
class SoftDeleteMixin:
    """Adds soft-delete capability with deleted_at and is_deleted columns."""

    is_deleted: bool = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at: datetime = Column(DateTime(timezone=True), nullable=True)


@declarative_mixin
class UUIDMixin:
    """Adds a UUID primary key column."""

    id: str = Column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )


@declarative_mixin
class TenantMixin:
    """Adds a tenant/user ID column for multi-tenant data isolation."""

    @declared_attr
    def user_id(cls) -> Column:
        return Column(
            String(36),
            nullable=False,
            index=True,
        )


class BaseModel(TimestampMixin, SoftDeleteMixin, UUIDMixin):
    """
    Abstract base model combining all mixins.
    All domain models should inherit from this.
    """
    __abstract__ = True
    __allow_unmapped__ = True
