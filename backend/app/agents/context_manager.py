"""
Zentar Intelligence — Context Manager

Token counting, context window management, and compression
for efficient LLM context utilization.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.services.ai_service import count_tokens

logger = logging.getLogger("zentar.agents.context")

settings = get_settings()

# Context limits per model family
MODEL_CONTEXT_LIMITS: Dict[str, int] = {
    "gpt-4o": 128000,
    "gpt-4-turbo": 128000,
    "gpt-4": 8192,
    "gpt-3.5-turbo": 16384,
    "claude-sonnet-4-20250514": 200000,
    "claude-3-5-sonnet-20241022": 200000,
    "claude-3-5-haiku-20241022": 200000,
    "claude-3-opus": 200000,
    "gemini-pro": 32768,
    "gemini-1.5-pro": 1048576,
    "deepseek-chat": 65536,
    "deepseek-reasoner": 65536,
}

# Recommended output token allocation (percentage of context)
OUTPUT_TOKEN_PERCENTAGE = 0.2


class ContextWindow:
    """Manages a context window for a single LLM request."""

    def __init__(
        self,
        model: str = "gpt-4o",
        provider: str = "openai",
        reserved_output_tokens: Optional[int] = None,
    ):
        self.model = model
        self.provider = provider
        self._max_context = MODEL_CONTEXT_LIMITS.get(model, 128000)
        self._reserved_output = reserved_output_tokens or int(
            self._max_context * OUTPUT_TOKEN_PERCENTAGE
        )
        self._max_input_tokens = self._max_context - self._reserved_output
        self._messages: List[Dict[str, str]] = []
        self._token_counts: List[int] = []

    @property
    def total_tokens(self) -> int:
        """Total tokens in the context window."""
        return sum(self._token_counts)

    @property
    def available_tokens(self) -> int:
        """Tokens still available for input."""
        return self._max_input_tokens - self.total_tokens

    @property
    def utilization(self) -> float:
        """Context utilization as a fraction (0-1)."""
        if self._max_input_tokens <= 0:
            return 1.0
        return self.total_tokens / self._max_input_tokens

    def add_message(self, role: str, content: str) -> int:
        """Add a message and return its token count."""
        tokens = count_tokens(content, self.model)
        self._messages.append({"role": role, "content": content})
        self._token_counts.append(tokens)
        return tokens

    def can_add(self, content: str) -> bool:
        """Check if content fits in the remaining context."""
        tokens = count_tokens(content, self.model)
        return self.total_tokens + tokens <= self._max_input_tokens

    def get_messages(self) -> List[Dict[str, str]]:
        """Get all messages in the window."""
        return self._messages

    def trim_to_fit(self, max_tokens: Optional[int] = None) -> List[Dict[str, str]]:
        """Trim oldest messages to fit within the token budget."""
        limit = max_tokens or self._max_input_tokens
        if self.total_tokens <= limit:
            return self._messages

        # Keep system messages, trim oldest user/assistant messages
        system_msgs = []
        others = []
        for msg, tokens in zip(self._messages, self._token_counts):
            if msg["role"] == "system":
                system_msgs.append(msg)
            else:
                others.append(msg)

        system_tokens = sum(
            count_tokens(m["content"], self.model) for m in system_msgs
        )
        budget = limit - system_tokens
        trimmed = []
        trimmed_tokens = 0

        # Keep newest messages
        for msg in reversed(others):
            tokens = count_tokens(msg["content"], self.model)
            if trimmed_tokens + tokens <= budget:
                trimmed.insert(0, msg)
                trimmed_tokens += tokens

        result = system_msgs + trimmed
        logger.info(
            "Trimmed context: %d -> %d messages (%d -> %d tokens)",
            len(self._messages),
            len(result),
            self.total_tokens,
            system_tokens + trimmed_tokens,
        )
        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get context window statistics."""
        return {
            "model": self.model,
            "max_context": self._max_context,
            "reserved_output": self._reserved_output,
            "max_input": self._max_input_tokens,
            "used_input": self.total_tokens,
            "available": self.available_tokens,
            "utilization": round(self.utilization, 3),
            "message_count": len(self._messages),
        }

    def clear(self):
        """Clear all messages."""
        self._messages = []
        self._token_counts = []


class ContextManager:
    """Manages context windows across multiple requests and conversations."""

    def __init__(self):
        self._windows: Dict[str, ContextWindow] = {}

    def create_window(
        self,
        window_id: str,
        model: str = "gpt-4o",
        provider: str = "openai",
        reserved_output_tokens: Optional[int] = None,
    ) -> ContextWindow:
        """Create a new context window."""
        self._windows[window_id] = ContextWindow(
            model=model,
            provider=provider,
            reserved_output_tokens=reserved_output_tokens,
        )
        return self._windows[window_id]

    def get_window(self, window_id: str) -> Optional[ContextWindow]:
        """Get an existing context window."""
        return self._windows.get(window_id)

    def delete_window(self, window_id: str):
        """Delete a context window."""
        self._windows.pop(window_id, None)

    def optimize(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o",
        max_tokens: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """Optimize a message list to fit within context limits."""
        window = ContextWindow(model=model)
        for msg in messages:
            window.add_message(msg["role"], msg.get("content", ""))

        if max_tokens:
            return window.trim_to_fit(max_tokens)

        # Default: trim if over 90% utilization
        if window.utilization > 0.9:
            return window.trim_to_fit(
                int(window._max_input_tokens * 0.9)
            )
        return messages

    def estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Estimate total tokens for a list of messages."""
        return sum(count_tokens(m.get("content", "")) for m in messages)

    def compress_context(
        self,
        messages: List[Dict[str, str]],
        preserve_recent: int = 2,
    ) -> Tuple[List[Dict[str, str]], Optional[str]]:
        """Compress context by identifying redundant messages.

        Returns (optimized_messages, summary_of_removed).
        """
        if len(messages) <= preserve_recent + 1:
            return messages, None

        # Keep system + recent messages, suggest summarization for the rest
        system = [m for m in messages if m["role"] == "system"]
        recent = messages[-preserve_recent:]
        to_summarize = messages[len(system):-preserve_recent]

        if not to_summarize:
            return messages, None

        summary = "Previous conversation:\n" + "\n".join(
            f"{m['role']}: {m['content'][:200]}"
            for m in to_summarize
        )
        return system + recent, summary

    def get_optimal_model(self, token_count: int) -> Tuple[str, str]:
        """Suggest optimal model based on token count."""
        if token_count <= 8000:
            return "gpt-4o-mini", "openai"
        elif token_count <= 32000:
            return "gpt-4o", "openai"
        elif token_count <= 128000:
            return "claude-sonnet-4-20250514", "anthropic"
        else:
            return "gemini-1.5-pro", "gemini"


# Global context manager
context_manager = ContextManager()
