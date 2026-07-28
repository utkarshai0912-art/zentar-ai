"""
Zentar Intelligence — Embedding Service

Text embedding generation and similarity search for semantic memory.
Supports multiple embedding providers with caching.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import numpy as np

from app.core.config import get_settings

logger = logging.getLogger("zentar.services.embeddings")

settings = get_settings()


class EmbeddingService:
    """Generates and compares text embeddings for semantic search.

    Supports OpenAI, local models, and cached embeddings.
    """

    def __init__(self):
        self._cache: Dict[str, Tuple[List[float], float]] = {}  # text -> (embedding, timestamp)
        self._cache_ttl = 3600  # 1 hour
        self._dimension = 1536  # Default OpenAI embedding dimension

    async def embed_text(self, text: str, provider: str = "openai") -> List[float]:
        """Generate embedding vector for a text string.

        Args:
            text: Text to embed
            provider: Embedding provider (openai, local)

        Returns:
            Embedding vector as list of floats
        """
        # Check cache
        cached = self._check_cache(text)
        if cached is not None:
            return cached

        embedding = await self._embed_openai(text)
        self._cache[text] = (embedding, time.time())
        return embedding

    async def embed_batch(self, texts: List[str], provider: str = "openai") -> List[List[float]]:
        """Generate embeddings for multiple texts efficiently."""
        results = []
        uncached_texts = []
        uncached_indices = []

        for i, text in enumerate(texts):
            cached = self._check_cache(text)
            if cached is not None:
                results.append(cached)
            else:
                results.append(None)
                uncached_texts.append(text)
                uncached_indices.append(i)

        if uncached_texts:
            batch_embeddings = await self._embed_openai_batch(uncached_texts)
            for idx, emb in zip(uncached_indices, batch_embeddings):
                results[idx] = emb
                self._cache[texts[idx]] = (emb, time.time())

        return [r for r in results if r is not None]

    async def _embed_openai(self, text: str) -> List[float]:
        """Embed using OpenAI-compatible API."""
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            logger.warning("No OpenAI API key for embeddings, using fallback")
            return self._fallback_embed(text)

        url = f"{settings.OPENAI_BASE_URL.rstrip('/')}/embeddings"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "input": text,
                        "model": "text-embedding-3-small",
                    },
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["data"][0]["embedding"]
                    else:
                        logger.warning("OpenAI embedding failed: %d", resp.status)
                        return self._fallback_embed(text)
            except Exception as e:
                logger.warning("OpenAI embedding error: %s", e)
                return self._fallback_embed(text)

    async def _embed_openai_batch(self, texts: List[str]) -> List[List[float]]:
        """Batch embed using OpenAI API."""
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            return [self._fallback_embed(t) for t in texts]

        url = f"{settings.OPENAI_BASE_URL.rstrip('/')}/embeddings"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "input": texts,
                        "model": "text-embedding-3-small",
                    },
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Sort by index to maintain order
                        sorted_data = sorted(data["data"], key=lambda x: x["index"])
                        return [d["embedding"] for d in sorted_data]
            except Exception as e:
                logger.warning("Batch embedding error: %s", e)

            return [self._fallback_embed(t) for t in texts]

    def _fallback_embed(self, text: str) -> List[float]:
        """Generate a deterministic fallback embedding when API is unavailable."""
        import hashlib
        # Create a pseudo-embedding from text hash for basic similarity
        hash_bytes = hashlib.md5(text.encode()).digest()
        np.random.seed(int.from_bytes(hash_bytes, "big") % (2**31))
        embedding = np.random.randn(self._dimension).tolist()
        # Normalize
        norm = np.linalg.norm(embedding)
        return (np.array(embedding) / norm).tolist()

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        a_arr = np.array(a)
        b_arr = np.array(b)
        dot = np.dot(a_arr, b_arr)
        norm = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
        if norm == 0:
            return 0.0
        return float(dot / norm)

    def _check_cache(self, text: str) -> Optional[List[float]]:
        """Check if text has a cached embedding."""
        if text in self._cache:
            emb, timestamp = self._cache[text]
            if time.time() - timestamp < self._cache_ttl:
                return emb
            del self._cache[text]
        return None

    def clear_cache(self):
        """Clear the embedding cache."""
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "cache_size": len(self._cache),
            "dimension": self._dimension,
        }


# Global embedding service
embedding_service = EmbeddingService()
