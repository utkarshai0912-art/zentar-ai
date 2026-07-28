"""
Zentar Intelligence — Memory Manager

Manages conversation history with sliding windows, summarization,
and long-term memory integration for agent context.
"""

import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.services.ai_service import count_tokens, provider_registry

logger = logging.getLogger("zentar.agents.memory")

settings = get_settings()


class ConversationMemory:
    """Manages conversation history for a single conversation session."""

    def __init__(
        self,
        conversation_id: str,
        max_tokens: int = 128000,
        summarize_threshold: float = 0.75,
    ):
        self.conversation_id = conversation_id
        self.max_tokens = max_tokens
        self.summarize_threshold = summarize_threshold
        self._messages: List[Dict[str, Any]] = []
        self._summary: Optional[str] = None
        self._system_prompt: Optional[str] = None

    @property
    def token_count(self) -> int:
        """Approximate token count of all messages."""
        total = 0
        if self._system_prompt:
            total += count_tokens(self._system_prompt)
        if self._summary:
            total += count_tokens(self._summary)
        for msg in self._messages:
            total += count_tokens(msg.get("content", ""))
        return total

    @property
    def messages(self) -> List[Dict[str, str]]:
        """Get messages formatted for API consumption."""
        result = []
        if self._system_prompt:
            result.append({"role": "system", "content": self._system_prompt})
        if self._summary:
            result.append({
                "role": "system",
                "content": f"<conversation_summary>\n{self._summary}\n</conversation_summary>",
            })
        result.extend(self._messages)
        return result

    def set_system_prompt(self, prompt: str):
        """Set or update the system prompt."""
        self._system_prompt = prompt

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to the conversation history."""
        self._messages.append({
            "role": role,
            "content": content,
            **(metadata or {}),
        })

    def needs_summarization(self) -> bool:
        """Check if the conversation exceeds the summarization threshold."""
        if self.max_tokens <= 0:
            return False
        return self.token_count > self.max_tokens * self.summarize_threshold

    async def summarize(self, provider: Optional[str] = None) -> str:
        """Summarize older messages to fit within context window."""
        if len(self._messages) <= 2:
            return self._summary or ""

        # Take recent messages and summarize the rest
        recent_count = max(4, len(self._messages) // 3)
        recent = self._messages[-recent_count:]
        to_summarize = self._messages[:-recent_count]

        summary_text = "\n".join(
            f"{m['role']}: {m['content'][:500]}"
            for m in to_summarize
        )

        summarize_prompt = (
            "Summarize the following conversation concisely, "
            "preserving key information, decisions, and context:\n\n"
            f"{summary_text}"
        )

        try:
            async for event in provider_registry.route_request(
                messages=[{"role": "user", "content": summarize_prompt}],
                provider_name=provider,
                model=None,
                temperature=0.3,
                max_tokens=2048,
                stream=False,
            ):
                if event["type"] == "done":
                    self._summary = event.get("content", "")
                    self._messages = recent
                    logger.info(
                        "Summarized conversation %s: %d -> %d messages",
                        self.conversation_id,
                        len(to_summarize) + len(recent),
                        len(recent),
                    )
        except Exception as e:
            logger.warning("Summarization failed for %s: %s", self.conversation_id, e)

        return self._summary or ""

    def get_context_window(self) -> List[Dict[str, str]]:
        """Get messages within the token limit, trimming if needed."""
        messages = self.messages

        # Count tokens
        total = sum(count_tokens(m.get("content", "")) for m in messages)
        if total <= self.max_tokens:
            return messages

        # Remove oldest non-system messages until under limit
        result = [m for m in messages if m["role"] == "system"]
        remaining = [m for m in messages if m["role"] != "system"]

        # Keep newest messages
        for m in reversed(remaining):
            msg_tokens = count_tokens(m.get("content", ""))
            current_total = sum(count_tokens(r.get("content", "")) for r in result)
            if current_total + msg_tokens <= self.max_tokens:
                result.insert(len(result) - len(remaining) + remaining.index(m), m)

        logger.info(
            "Trimmed context for %s: %d -> %d messages",
            self.conversation_id,
            len(messages),
            len(result),
        )
        return result

    def clear(self):
        """Clear all messages but keep system prompt."""
        self._messages = []
        self._summary = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize memory state."""
        return {
            "conversation_id": self.conversation_id,
            "message_count": len(self._messages),
            "token_count": self.token_count,
            "has_summary": self._summary is not None,
            "has_system_prompt": self._system_prompt is not None,
        }


class MemoryManager:
    """Manages multiple conversation memories across sessions."""

    def __init__(self):
        self._memories: Dict[str, ConversationMemory] = {}
        self._max_sessions = 100

    def get_or_create(self, conversation_id: str, **kwargs) -> ConversationMemory:
        """Get existing memory or create a new one."""
        if conversation_id not in self._memories:
            if len(self._memories) >= self._max_sessions:
                # Evict oldest
                oldest = min(self._memories.keys(), key=lambda k: id(self._memories[k]))
                del self._memories[oldest]
                logger.info("Evicted memory session: %s", oldest)

            self._memories[conversation_id] = ConversationMemory(
                conversation_id=conversation_id,
                **{k: v for k, v in kwargs.items() if k in ("max_tokens", "summarize_threshold")},
            )
        return self._memories[conversation_id]

    def get(self, conversation_id: str) -> Optional[ConversationMemory]:
        """Get existing memory if it exists."""
        return self._memories.get(conversation_id)

    def delete(self, conversation_id: str):
        """Delete a memory session."""
        self._memories.pop(conversation_id, None)

    def cleanup_inactive(self, max_age_minutes: int = 60):
        """Remove inactive memory sessions."""
        # Simplified: we don't track access time currently
        if len(self._memories) > self._max_sessions:
            excess = len(self._memories) - self._max_sessions
            keys = list(self._memories.keys())[:excess]
            for k in keys:
                del self._memories[k]
            logger.info("Cleaned up %d inactive memory sessions", excess)

    def get_stats(self) -> Dict[str, Any]:
        """Get memory manager statistics."""
        return {
            "active_sessions": len(self._memories),
            "max_sessions": self._max_sessions,
        }


# Global memory manager instance
memory_manager = MemoryManager()
