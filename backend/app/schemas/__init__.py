"""
Zentar Intelligence — Pydantic Schemas

Request/response schemas for all API endpoints.
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, EmailStr, Field

# ──────────────────────────────────────────
# Generic API Response
# ──────────────────────────────────────────

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""
    success: bool = True
    message: str = "Success"
    data: Optional[T] = None
    error: Optional[str] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


# ──────────────────────────────────────────
# Auth
# ──────────────────────────────────────────

class AuthRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=100)


class AuthLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthRefreshRequest(BaseModel):
    refresh_token: str


class UserProfileResponse(BaseModel):
    id: str
    email: str
    display_name: str
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    role: str
    theme: str
    language: str
    created_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────
# Conversation
# ──────────────────────────────────────────

class ConversationCreateRequest(BaseModel):
    title: Optional[str] = "New Conversation"
    model_id: Optional[str] = None
    provider: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096


class ConversationUpdateRequest(BaseModel):
    title: Optional[str] = None
    is_archived: Optional[bool] = None
    is_pinned: Optional[bool] = None


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    content_type: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    status: str
    provider: Optional[str] = None
    model: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: str
    title: str
    model_id: Optional[str] = None
    provider: Optional[str] = None
    temperature: float
    max_tokens: int
    is_archived: bool
    is_pinned: bool
    message_count: int
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: Optional[str] = None
    model_id: Optional[str] = None
    provider: Optional[str] = None
    stream: bool = True
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None


class ChatStreamEvent(BaseModel):
    type: str  # chunk, done, error, tool_call
    content: Optional[str] = None
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    error: Optional[str] = None


# ──────────────────────────────────────────
# AI Providers & Models
# ──────────────────────────────────────────

class ProviderResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: str
    is_configured: bool
    is_enabled: bool
    models: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True


class ModelResponse(BaseModel):
    id: str
    provider: str
    name: str
    display_name: str
    context_length: int
    supports_streaming: bool
    supports_reasoning: bool
    is_default: bool
    is_enabled: bool

    class Config:
        from_attributes = True


# ──────────────────────────────────────────
# MCP
# ──────────────────────────────────────────

class MCPServerCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    url: str = Field(..., min_length=1)
    type: str = "remote"  # remote, local
    auth_type: Optional[str] = None  # oauth, token, none
    auth_token: Optional[str] = None
    description: Optional[str] = None


class MCPServerResponse(BaseModel):
    id: str
    name: str
    url: str
    type: str
    is_connected: bool
    is_enabled: bool
    tools_count: int
    resources_count: int
    prompts_count: int

    class Config:
        from_attributes = True


# ──────────────────────────────────────────
# Plugins
# ──────────────────────────────────────────

class PluginInstallRequest(BaseModel):
    source: str  # marketplace name, URL, or local path
    source_type: str = "marketplace"  # marketplace, url, local
    config: Optional[Dict[str, Any]] = None


class PluginResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: Optional[str]
    version: str
    author: Optional[str]
    is_enabled: bool
    is_official: bool
    installed_at: datetime

    class Config:
        from_attributes = True


# ──────────────────────────────────────────
# Skills
# ──────────────────────────────────────────

class SkillInstallRequest(BaseModel):
    source: str
    source_type: str = "marketplace"
    config: Optional[Dict[str, Any]] = None


class SkillResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: Optional[str]
    version: str
    author: Optional[str]
    category: str
    is_enabled: bool
    is_official: bool

    class Config:
        from_attributes = True


# ──────────────────────────────────────────
# Memory
# ──────────────────────────────────────────

class MemoryCreateRequest(BaseModel):
    content: str = Field(..., min_length=1)
    memory_type: str = "note"
    scope: str = "user"
    importance: int = Field(default=0, ge=0, le=10)
    tags: List[str] = []
    project_id: Optional[str] = None
    context: Dict[str, Any] = {}


class MemoryUpdateRequest(BaseModel):
    content: Optional[str] = None
    importance: Optional[int] = None
    tags: Optional[List[str]] = None


class MemoryResponse(BaseModel):
    id: str
    content: str
    memory_type: str
    scope: str
    importance: int
    tags: List[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MemorySearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    memory_type: Optional[str] = None
    limit: int = 10


# ──────────────────────────────────────────
# Admin
# ──────────────────────────────────────────

class AdminUserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    is_active: bool
    is_superuser: bool
    total_conversations: int
    total_tokens_used: int
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class SystemStatsResponse(BaseModel):
    total_users: int
    total_conversations: int
    total_messages: int
    total_tokens_used: int
    active_users_last_24h: int
    active_plugins: int
    active_skills: int
    storage_used_mb: float
