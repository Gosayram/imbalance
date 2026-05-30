from __future__ import annotations

import hashlib
import logging
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CacheEntry:
	"""Cache entry for embedding."""
	embedding: list[float]
	dimensions: int
	model: str


class EmbeddingCache:
	"""LRU cache for embeddings."""

	def __init__(self, maxsize: int = 10000) -> None:
		self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
		self._maxsize = maxsize
		self._hits = 0
		self._misses = 0

	def _make_key(self, text: str, model: str) -> str:
		"""Make cache key from text and model."""
		return hashlib.sha256(f'{model}:{text}'.encode()).hexdigest()

	def get(self, text: str, model: str) -> list[float] | None:
		"""Get embedding from cache.

		Args:
			text: Input text
			model: Model name

		Returns:
			Cached embedding or None
		"""
		key = self._make_key(text, model)
		entry = self._cache.get(key)

		if entry is not None:
			self._hits += 1
			# Move to end (most recently used)
			self._cache.move_to_end(key)
			return entry.embedding

		self._misses += 1
		return None

	def put(self, text: str, model: str, embedding: list[float]) -> None:
		"""Store embedding in cache.

		Args:
			text: Input text
			model: Model name
			embedding: Embedding vector
		"""
		key = self._make_key(text, model)

		# Remove oldest if at capacity
		if len(self._cache) >= self._maxsize:
			self._cache.popitem(last=False)

		self._cache[key] = CacheEntry(
			embedding=embedding,
			dimensions=len(embedding),
			model=model,
		)

	def clear(self) -> None:
		"""Clear cache."""
		self._cache.clear()
		self._hits = 0
		self._misses = 0

	@property
	def size(self) -> int:
		"""Get cache size."""
		return len(self._cache)

	@property
	def hit_rate(self) -> float:
		"""Get cache hit rate."""
		total = self._hits + self._misses
		if total == 0:
			return 0.0
		return self._hits / total

	@property
	def stats(self) -> dict[str, Any]:
		"""Get cache statistics."""
		return {
			'size': self.size,
			'maxsize': self._maxsize,
			'hits': self._hits,
			'misses': self._misses,
			'hit_rate': self.hit_rate,
		}


# Global embedding cache
_global_cache: EmbeddingCache | None = None


def get_embedding_cache() -> EmbeddingCache:
	"""Get global embedding cache."""
	global _global_cache
	if _global_cache is None:
		_global_cache = EmbeddingCache()
	return _global_cache


def set_embedding_cache(cache: EmbeddingCache) -> None:
	"""Set global embedding cache."""
	global _global_cache
	_global_cache = cache
