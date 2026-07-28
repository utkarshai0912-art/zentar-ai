"""
Zentar Intelligence — Core Configuration

Centralized settings management using Pydantic's BaseSettings.
All environment variables are loaded from Railway's environment or .env file.
"""

import os
from datetime import timedelta
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Zentar Intelligence"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["*"]
    ALLOWED_HOSTS: List[str] = ["*"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/zentar"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10

    # JWT Authentication
    JWT_SECRET_KEY: str = "change-me-in-production-use-a-real-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "zentar-intelligence"

    # OAuth
    OAUTH_GOOGLE_CLIENT_ID: Optional[str] = None
    OAUTH_GOOGLE_CLIENT_SECRET: Optional[str] = None
    OAUTH_GITHUB_CLIENT_ID: Optional[str] = None
    OAUTH_GITHUB_CLIENT_SECRET: Optional[str] = None

    # Encryption
    ENCRYPTION_KEY: str = "change-me-in-production-use-a-real-32-byte-key!"
    ENCRYPTION_ALGORITHM: str = "AES-256-GCM"

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # AI Providers
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_DEFAULT_MODEL: str = "gpt-4o"

    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_BASE_URL: str = "https://api.anthropic.com/v1"
    ANTHROPIC_DEFAULT_MODEL: str = "claude-sonnet-4-20250514"

    GEMINI_API_KEY: Optional[str] = None
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"

    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_DEFAULT_MODEL: str = "deepseek-chat"

    QWEN_API_KEY: Optional[str] = None
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_DEFAULT_MODEL: str = "llama3"

    # Web Search
    SERPAPI_API_KEY: Optional[str] = None
    TAVILY_API_KEY: Optional[str] = None

    # File Storage
    UPLOAD_DIR: str = "/data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: List[str] = [
        ".txt", ".py", ".js", ".ts", ".java", ".kt", ".swift",
        ".md", ".json", ".yaml", ".xml", ".html", ".css",
        ".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg", ".gif",
        ".zip", ".tar", ".gz", ".csv", ".sql",
    ]

    # Plugin System
    PLUGIN_DIR: str = "/data/plugins"
    PLUGIN_SANDBOX_ENABLED: bool = True
    PLUGIN_MAX_MEMORY_MB: int = 256
    PLUGIN_EXECUTION_TIMEOUT_SECONDS: int = 30

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    AUDIT_LOG_ENABLED: bool = True

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MAX_MESSAGE_SIZE: int = 10 * 1024 * 1024  # 10MB

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Returns cached application settings singleton."""
    return Settings()
