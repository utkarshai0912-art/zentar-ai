"""
Zentar Intelligence — AI Provider Service

Multi-provider AI service with routing, fallback, and streaming.
Supports OpenAI, Anthropic, Google Gemini, DeepSeek, Qwen, Ollama, OpenRouter.
"""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import aiohttp
import tiktoken
from fastapi import HTTPException

from app.core.config import get_settings

settings = get_settings()


# ──────────────────────────────────────────
# Token Counting
# ──────────────────────────────────────────

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Approximate token count using tiktoken."""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback: ~4 chars per token
        return len(text) // 4


# ──────────────────────────────────────────
# Base Provider
# ──────────────────────────────────────────

class AIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, name: str, api_key: Optional[str], base_url: str):
        self.name = name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Send a chat completion request with optional streaming."""
        ...

    @abstractmethod
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models from this provider."""
        ...

    def is_configured(self) -> bool:
        """Check if the provider has the required API key."""
        return bool(self.api_key)


# ──────────────────────────────────────────
# OpenAI Provider
# ──────────────────────────────────────────

class OpenAIProvider(AIProvider):
    """OpenAI / compatible API provider."""

    def __init__(self):
        super().__init__(
            name="openai",
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
            ) as resp:
                if resp.status != 200:
                    error_body = await resp.text()
                    yield {"type": "error", "error": f"OpenAI API error {resp.status}: {error_body}"}
                    return

                if stream:
                    async for line in resp.content:
                        line = line.decode("utf-8").strip()
                        if not line or line == "data: [DONE]":
                            continue
                        if line.startswith("data: "):
                            data = json.loads(line[6:])
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            finish = data.get("choices", [{}])[0].get("finish_reason")
                            if delta.get("content"):
                                yield {
                                    "type": "chunk",
                                    "content": delta["content"],
                                }
                            if finish:
                                usage = data.get("usage", {})
                                yield {
                                    "type": "done",
                                    "finish_reason": finish,
                                    "usage": {
                                        "input_tokens": usage.get("prompt_tokens", 0),
                                        "output_tokens": usage.get("completion_tokens", 0),
                                    },
                                }
                else:
                    data = await resp.json()
                    choice = data["choices"][0]
                    yield {
                        "type": "done",
                        "content": choice["message"]["content"],
                        "finish_reason": choice.get("finish_reason"),
                        "usage": {
                            "input_tokens": data["usage"]["prompt_tokens"],
                            "output_tokens": data["usage"]["completion_tokens"],
                        },
                    }

    async def list_models(self) -> List[Dict[str, Any]]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(f"{self.base_url}/models") as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return [
                    {
                        "id": m["id"],
                        "provider": "openai",
                        "name": m["id"],
                        "context_length": 128000 if "gpt-4" in m["id"] else 8192,
                    }
                    for m in data.get("data", [])
                ]


# ──────────────────────────────────────────
# Anthropic Provider
# ──────────────────────────────────────────

class AnthropicProvider(AIProvider):
    """Anthropic Claude API provider."""

    def __init__(self):
        super().__init__(
            name="anthropic",
            api_key=settings.ANTHROPIC_API_KEY,
            base_url=settings.ANTHROPIC_BASE_URL,
        )

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-sonnet-4-20250514",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        # Convert OpenAI format to Anthropic format
        system_prompt = None
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(
                f"{self.base_url}/messages",
                json=payload,
            ) as resp:
                if resp.status != 200:
                    error_body = await resp.text()
                    yield {"type": "error", "error": f"Anthropic API error {resp.status}: {error_body}"}
                    return

                if stream:
                    async for line in resp.content:
                        line = line.decode("utf-8").strip()
                        if not line or not line.startswith("data: "):
                            continue
                        data = json.loads(line[6:])
                        if data["type"] == "content_block_delta":
                            yield {"type": "chunk", "content": data["delta"].get("text", "")}
                        elif data["type"] == "message_done":
                            usage = data.get("usage", {})
                            yield {
                                "type": "done",
                                "finish_reason": data.get("stop_reason", "end_turn"),
                                "usage": {
                                    "input_tokens": usage.get("input_tokens", 0),
                                    "output_tokens": usage.get("output_tokens", 0),
                                },
                            }
                else:
                    data = await resp.json()
                    yield {
                        "type": "done",
                        "content": data["content"][0]["text"],
                        "finish_reason": data.get("stop_reason"),
                        "usage": {
                            "input_tokens": data["usage"]["input_tokens"],
                            "output_tokens": data["usage"]["output_tokens"],
                        },
                    }

    async def list_models(self) -> List[Dict[str, Any]]:
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(f"{self.base_url}/models") as resp:
                if resp.status != 200:
                    return self._default_models()
                data = await resp.json()
                return [
                    {
                        "id": m["id"],
                        "provider": "anthropic",
                        "name": m["id"],
                        "context_length": m.get("context_length", 200000),
                    }
                    for m in data.get("data", [])
                ]

    def _default_models(self) -> List[Dict[str, Any]]:
        return [
            {"id": "claude-sonnet-4-20250514", "provider": "anthropic", "name": "Claude Sonnet 4", "context_length": 200000},
            {"id": "claude-3-5-sonnet-20241022", "provider": "anthropic", "name": "Claude 3.5 Sonnet", "context_length": 200000},
            {"id": "claude-3-5-haiku-20241022", "provider": "anthropic", "name": "Claude 3.5 Haiku", "context_length": 200000},
        ]


# ──────────────────────────────────────────
# Google Gemini Provider
# ──────────────────────────────────────────

class GeminiProvider(AIProvider):
    """Google Gemini API provider."""

    def __init__(self):
        super().__init__(
            name="gemini",
            api_key=settings.GEMINI_API_KEY,
            base_url=settings.GEMINI_BASE_URL,
        )

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gemini-pro",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        # Convert messages to Gemini format
        gemini_contents = []
        for msg in messages:
            if msg["role"] in ("user", "assistant"):
                gemini_contents.append({
                    "role": "user" if msg["role"] == "user" else "model",
                    "parts": [{"text": msg["content"]}],
                })

        headers = {"Content-Type": "application/json"}
        url = f"{self.base_url}/models/{model}:streamGenerateContent" if stream else f"{self.base_url}/models/{model}:generateContent"
        url += f"?key={self.api_key}"

        payload = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    error_body = await resp.text()
                    yield {"type": "error", "error": f"Gemini API error {resp.status}: {error_body}"}
                    return

                data = await resp.json()
                if stream:
                    candidates = data if isinstance(data, list) else [data]
                    for candidate in candidates:
                        parts = (candidate.get("candidates", [{}])[0]
                                 .get("content", {})
                                 .get("parts", []))
                        for part in parts:
                            if "text" in part:
                                yield {"type": "chunk", "content": part["text"]}
                    yield {"type": "done", "finish_reason": "stop"}
                else:
                    text = ""
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join(p.get("text", "") for p in parts)
                    yield {"type": "done", "content": text, "finish_reason": "stop"}

    async def list_models(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/models?key={self.api_key}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return [
                    {"id": m["name"].split("/")[-1], "provider": "gemini", "name": m["displayName"], "context_length": 32768}
                    for m in data.get("models", [])
                    if "generateContent" in m.get("supportedGenerationMethods", [])
                ]


# ──────────────────────────────────────────
# DeepSeek Provider
# ──────────────────────────────────────────

class DeepSeekProvider(AIProvider):
    """DeepSeek API provider (OpenAI-compatible)."""

    def __init__(self):
        super().__init__(
            name="deepseek",
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
        )

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        provider = OpenAIProvider()
        provider.api_key = self.api_key
        provider.base_url = self.base_url
        async for event in provider.chat_completion(messages, model, temperature, max_tokens, stream):
            yield event

    async def list_models(self) -> List[Dict[str, Any]]:
        return [
            {"id": "deepseek-chat", "provider": "deepseek", "name": "DeepSeek Chat", "context_length": 65536},
            {"id": "deepseek-reasoner", "provider": "deepseek", "name": "DeepSeek Reasoner", "context_length": 65536},
        ]


# ──────────────────────────────────────────
# Provider Registry
# ──────────────────────────────────────────

class AIProviderRegistry:
    """Registry for all AI providers with routing and fallback."""

    def __init__(self):
        self._providers: Dict[str, AIProvider] = {}
        self._register_defaults()

    def _register_defaults(self):
        providers = [
            OpenAIProvider(),
            AnthropicProvider(),
            GeminiProvider(),
            DeepSeekProvider(),
        ]
        for p in providers:
            self._providers[p.name] = p

    def register(self, name: str, provider: AIProvider):
        """Register a custom provider."""
        self._providers[name] = provider

    def get_provider(self, name: str) -> Optional[AIProvider]:
        """Get a provider by name."""
        return self._providers.get(name)

    def get_configured_providers(self) -> Dict[str, AIProvider]:
        """Get all providers with valid API keys."""
        return {k: v for k, v in self._providers.items() if v.is_configured()}

    def list_providers(self) -> List[Dict[str, Any]]:
        """List all registered providers with their status."""
        return [
            {
                "id": name,
                "name": name,
                "display_name": name.capitalize(),
                "description": f"{name.capitalize()} AI provider",
                "is_configured": p.is_configured(),
                "is_enabled": True,
            }
            for name, p in self._providers.items()
        ]

    async def route_request(
        self,
        messages: List[Dict[str, str]],
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = True,
        user_id: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Route a chat request to the appropriate provider.
        Supports automatic fallback if primary provider fails.
        If user_id is provided, fetches user's credentials from the vault.
        """
        resolved_providers = []
        resolved_model = model
        user_config = None

        # If user_id is given, try to get their credentials
        if user_id:
            try:
                from app.services.vault_service import VaultService
                from app.core.database import AsyncSessionLocal

                async with AsyncSessionLocal() as db:
                    vault = VaultService(db)
                    user_config = await vault.get_user_provider_config(user_id)
            except Exception:
                pass

        # Build provider list with user credentials if available
        if user_config and user_config.get(provider_name or "openai"):
            # User has configured the requested provider
            cfg = user_config.get(provider_name or "openai")
            provider = OpenAIProvider()
            provider.api_key = cfg.get("api_key")
            provider.base_url = cfg.get("base_url") or provider.base_url
            resolved_providers = [provider]
            if not resolved_model and cfg.get("default_model"):
                resolved_model = cfg["default_model"]
        elif provider_name and provider_name in self._providers:
            resolved_providers = [self._providers[provider_name]]
        else:
            configured = self.get_configured_providers()
            if user_config:
                order = ["openai", "anthropic", "gemini", "deepseek", "openrouter", "groq", "mistral"]
                for name in order:
                    if name in user_config and name in self._providers:
                        cfg = user_config[name]
                        p = self._providers[name]
                        p.api_key = cfg.get("api_key") or p.api_key
                        p.base_url = cfg.get("base_url") or p.base_url
                        resolved_providers.append(p)
                        if not resolved_model and cfg.get("default_model"):
                            resolved_model = cfg["default_model"]
            else:
                order = ["openai", "anthropic", "gemini", "deepseek"]
                for p in order:
                    if p in configured:
                        resolved_providers.append(configured[p])

        if not resolved_providers:
            yield {"type": "error", "error": "No AI providers are configured. Please add an API key in Settings."}
            return

        # Determine model
        resolved_model = resolved_model or self._get_default_model(resolved_providers[0].name)

        # Try each provider with fallback
        last_error = None
        for provider in resolved_providers:
            try:
                async for event in provider.chat_completion(
                    messages=messages,
                    model=resolved_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream,
                ):
                    if event["type"] == "error" and not stream:
                        last_error = event["error"]
                        break
                    yield event
                return
            except Exception as e:
                last_error = str(e)
                continue

        yield {
            "type": "error",
            "error": f"All AI providers failed. Last error: {last_error}",
        }

    def _get_default_model(self, provider_name: str) -> str:
        defaults = {
            "openai": settings.OPENAI_DEFAULT_MODEL,
            "anthropic": settings.ANTHROPIC_DEFAULT_MODEL,
            "gemini": "gemini-pro",
            "deepseek": settings.DEEPSEEK_DEFAULT_MODEL,
        }
        return defaults.get(provider_name, "gpt-4o")


# Singleton registry
provider_registry = AIProviderRegistry()
