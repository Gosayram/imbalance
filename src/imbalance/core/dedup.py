from __future__ import annotations

import logging
from dataclasses import dataclass

import aiosqlite

logger = logging.getLogger(__name__)

JACCARD_THRESHOLD = 0.75


@dataclass(frozen=True)
class DedupResult:
	is_duplicate: bool
	existing_slug: str | None = None
	similarity: float = 0.0


def _jaccard_similarity(a: str, b: str) -> float:
	words_a = set(a.lower().split())
	words_b = set(b.lower().split())
	if not words_a or not words_b:
		return 0.0
	intersection = words_a & words_b
	union = words_a | words_b
	return len(intersection) / len(union)


async def dedup_check(
	db: aiosqlite.Connection,
	kb_name: str,
	new_content: str,
	section: str,
) -> DedupResult:
	rows = await db.execute_fetchall(
		'SELECT slug, content FROM wiki_sections WHERE kb_name=? AND section=? AND archived=FALSE',
		(kb_name, section),
	)

	if not rows:
		return DedupResult(is_duplicate=False)

	try:
		embedder = await _get_embedder()
		if embedder is not None:
			new_emb = (await embedder.embed([new_content]))[0]
			for r in rows:
				existing_content = r['content']
				existing_emb = (await embedder.embed([existing_content]))[0]
				sim = _cosine_similarity(new_emb, existing_emb)
				if sim > 0.92:
					return DedupResult(is_duplicate=True, existing_slug=r['slug'], similarity=sim)
			return DedupResult(is_duplicate=False)
	except Exception:
		pass

	for r in rows:
		sim = _jaccard_similarity(new_content, r['content'])
		if sim > JACCARD_THRESHOLD:
			return DedupResult(is_duplicate=True, existing_slug=r['slug'], similarity=sim)

	return DedupResult(is_duplicate=False)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
	dot = sum(x * y for x, y in zip(a, b, strict=False))
	norm_a = sum(x * x for x in a) ** 0.5
	norm_b = sum(x * x for x in b) ** 0.5
	if norm_a == 0 or norm_b == 0:
		return 0.0
	return dot / (norm_a * norm_b)


_embedder = None
_embedder_loaded = False


async def _get_embedder():
	global _embedder, _embedder_loaded
	if _embedder_loaded:
		return _embedder
	_embedder_loaded = True
	try:
		from imbalance.core.embeddings import EmbeddingConfig, build_provider

		config = EmbeddingConfig(provider='ollama', model='nomic-embed-text:v1.5')
		embedder = await build_provider(config)
		if embedder is not None:
			_embedder = embedder
		return embedder
	except Exception:
		return None
