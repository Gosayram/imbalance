from __future__ import annotations

import hashlib
import time
from typing import Any

from cachetools import TTLCache

from imbalance.core.context import ContextChunk, ContextMode, ContextPack
from imbalance.storage.store import SQLiteStore

PRECEDENCE = [
	'current_task',
	'current_filesystem',
	'session_notes',
	'memory_summary',
	'wiki_sections',
	'archived',
]

COMPACTED_PRECEDENCE = [
	'compaction_checkpoint',
	'current_task',
	'memory_summary',
	'wiki_sections',
]

DEFAULT_SCOPE_WEIGHTS: dict[str, float] = {
	'decisions': 1.5,
	'context': 1.3,
	'stack': 1.0,
	'issues': 1.0,
	'about': 1.0,
}

RRF_K = 60


def _cache_key(query: str, budget_tokens: int, scope: tuple[str, ...] | None) -> str:
	parts = [query, str(budget_tokens)]
	if scope:
		parts.extend(sorted(scope))
	return hashlib.sha256('|'.join(parts).encode()).hexdigest()[:16]


def rrf_merge(
	fts_results: list[ContextChunk],
	vec_results: list[ContextChunk],
	scope_weights: dict[str, float] | None = None,
	confidence_weight: float = 0.05,
) -> list[ContextChunk]:
	weights = scope_weights or DEFAULT_SCOPE_WEIGHTS
	scores: dict[str, float] = {}
	chunks: dict[str, ContextChunk] = {}

	for rank, chunk in enumerate(fts_results):
		slug = chunk.slug
		section_weight = weights.get(chunk.section, 1.0)
		confidence_boost = confidence_weight * chunk.confidence
		scores[slug] = scores.get(slug, 0.0) + section_weight / (RRF_K + rank + 1) + confidence_boost
		chunks[slug] = chunk

	for rank, chunk in enumerate(vec_results):
		slug = chunk.slug
		section_weight = weights.get(chunk.section, 1.0)
		confidence_boost = confidence_weight * chunk.confidence
		scores[slug] = scores.get(slug, 0.0) + section_weight / (RRF_K + rank + 1) + confidence_boost
		if slug not in chunks:
			chunks[slug] = chunk

	ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
	return [chunks[slug] for slug, _ in ranked]


class QueryEngine:
	def __init__(
		self,
		store: SQLiteStore,
		memory_mode: ContextMode = ContextMode.READ_WRITE,
		cache_ttl: int = 1800,
		cache_maxsize: int = 256,
		embedding_provider: Any | None = None,
		scope_weights: dict[str, float] | None = None,
		confidence_weight: float = 0.05,
	) -> None:
		self.store = store
		self.memory_mode = memory_mode
		self._cache: TTLCache[str, ContextPack] = TTLCache(maxsize=cache_maxsize, ttl=cache_ttl)
		self._embedder = embedding_provider
		self._scope_weights = scope_weights
		self._confidence_weight = confidence_weight

	async def get_context_pack(
		self,
		query: str,
		*,
		budget_tokens: int = 2000,
		scope: list[str] | None = None,
		session_id: str | None = None,
		tags: list[str] | None = None,
	) -> ContextPack:
		compaction_chunk = None
		if session_id:
			compaction_chunk = await self._get_compaction_checkpoint(session_id)

		if compaction_chunk:
			return await self._post_compaction_restore(
				query, budget_tokens, scope, compaction_chunk
			)

		key = _cache_key(query, budget_tokens, tuple(scope) if scope else None)
		cached = self._cache.get(key)
		if cached is not None:
			return cached

		start = time.monotonic()
		result = await self._standard_search(query, budget_tokens, scope, tags)
		latency_ms = int((time.monotonic() - start) * 1000)
		self._cache[key] = result

		tokens_returned = sum(c.token_count for c in result.evidence)
		source = 'fts5' if self._embedder is None else 'fts5+vec'
		await self._log_retrieval(
			query, scope, len(result.evidence), tokens_returned,
			budget_tokens, latency_ms, source, session_id,
		)
		return result

	async def _standard_search(
		self,
		query: str,
		budget_tokens: int,
		scope: list[str] | None,
		tags: list[str] | None = None,
	) -> ContextPack:
		summary = None
		summary_budget = min(500, int(budget_tokens * 0.2))
		evidence_budget = budget_tokens

		if self.memory_mode != ContextMode.OFF:
			summary = await self.store.get_memory_summary(max_tokens=summary_budget)
			if summary:
				evidence_budget -= summary_budget

		evidence = await self._hybrid_search(query, scope, tags)

		linked_slugs = await self._expand_graph(evidence)
		if linked_slugs:
			linked_chunks = await self._fetch_linked(linked_slugs, scope)
			evidence = self._merge_linked(evidence, linked_chunks)

		selected = []
		used = 0
		omitted = []
		for chunk in evidence:
			if used + chunk.token_count > evidence_budget:
				omitted.append(chunk.slug)
				continue
			selected.append(chunk)
			used += chunk.token_count

		warnings = []
		if self.memory_mode == ContextMode.READ_ONLY:
			warnings.append('Memory is read-only for this run.')
		unconfirmed = [c.slug for c in selected if c.confidence < 0.2]
		if unconfirmed:
			warnings.append(f'[unconfirmed] {", ".join(unconfirmed)}')

		return ContextPack(
			query=query,
			budget_tokens=budget_tokens,
			precedence=PRECEDENCE,
			summary=summary,
			evidence=selected,
			omitted=omitted,
			warnings=warnings,
		)

	async def _hybrid_search(
		self, query: str, scope: list[str] | None, tags: list[str] | None = None
	) -> list[ContextChunk]:
		fts_results = await self.store.fts_search(query, limit=8, scope=scope, tags=tags)

		if self._embedder is None:
			return fts_results

		try:
			embeddings = await self._embedder.embed([query])
			vec_results = await self.store.vec_search(
				embeddings[0], limit=8, scope=scope
			)
			return rrf_merge(fts_results, vec_results, self._scope_weights, self._confidence_weight)
		except Exception:
			return fts_results

	async def _post_compaction_restore(
		self,
		query: str,
		budget_tokens: int,
		scope: list[str] | None,
		compaction_chunk: ContextChunk,
	) -> ContextPack:
		compaction_budget = int(budget_tokens * 0.4)
		regular_budget = budget_tokens - compaction_budget

		summary = await self.store.get_memory_summary(max_tokens=min(300, int(regular_budget * 0.2)))

		evidence = await self.store.fts_search(query, limit=6, scope=scope)
		selected: list[ContextChunk] = [compaction_chunk]
		used = compaction_chunk.token_count
		omitted = []
		for chunk in evidence:
			if used + chunk.token_count > regular_budget:
				omitted.append(chunk.slug)
				continue
			selected.append(chunk)
			used += chunk.token_count

		tokens_returned = sum(c.token_count for c in selected)
		await self._log_retrieval(
			query, scope, len(selected), tokens_returned,
			budget_tokens, 0, 'cache', None,
		)

		return ContextPack(
			query=query,
			budget_tokens=budget_tokens,
			precedence=COMPACTED_PRECEDENCE,
			summary=summary,
			evidence=selected,
			omitted=omitted,
			warnings=['Restored from compaction checkpoint.'],
		)

	async def _get_compaction_checkpoint(self, session_id: str) -> ContextChunk | None:
		row = await self.store.db.execute_fetchall(
			"""SELECT slug, section, content, token_count
			FROM wiki_sections
			WHERE kb_name=? AND compaction_point=TRUE AND session_id=?
			ORDER BY updated_at DESC LIMIT 1""",
			(self.store.kb_name, session_id),
		)
		if not row:
			return None
		r = row[0]
		return ContextChunk(
			slug=r['slug'],
			section=r['section'],
			content=r['content'],
			score=1.0,
			token_count=r['token_count'],
			confidence=1.0,
		)

	async def _expand_graph(self, evidence: list[ContextChunk]) -> dict[str, float]:
		from imbalance.core.links import expand_links

		slugs = [c.slug for c in evidence]
		return await expand_links(self.store.db, self.store.kb_name, slugs)

	async def _fetch_linked(
		self, linked_slugs: dict[str, float], scope: list[str] | None
	) -> list[ContextChunk]:
		if not linked_slugs:
			return []
		placeholders = ', '.join('?' for _ in linked_slugs)
		params: list[object] = [self.store.kb_name]
		params.extend(linked_slugs.keys())
		scope_sql = ''
		if scope:
			ph = ', '.join('?' for _ in scope)
			scope_sql = f'AND section IN ({ph})'
			params.extend(scope)
		rows = await self.store.db.execute_fetchall(
			f"""SELECT slug, section, content, token_count, confirmation_count
			FROM wiki_sections
			WHERE kb_name=? AND slug IN ({placeholders}) AND archived=FALSE {scope_sql}""",
			params,
		)
		return [
			ContextChunk(
				slug=r['slug'],
				section=r['section'],
				content=r['content'],
				score=linked_slugs.get(r['slug'], 0.5),
				token_count=int(r['token_count']),
				confidence=min(float(r['confirmation_count']) / 10.0, 1.0),
			)
			for r in rows
		]

	@staticmethod
	def _merge_linked(
		evidence: list[ContextChunk], linked: list[ContextChunk]
	) -> list[ContextChunk]:
		seen = {c.slug for c in evidence}
		merged = list(evidence)
		for chunk in linked:
			if chunk.slug not in seen:
				merged.append(chunk)
				seen.add(chunk.slug)
		return merged

	async def _log_retrieval(
		self,
		query: str,
		scope: list[str] | None,
		results_count: int,
		tokens_returned: int,
		tokens_budget: int,
		latency_ms: int,
		source: str,
		session_id: str | None,
	) -> None:
		await self.store.db.execute(
			"""
			INSERT INTO retrieval_log(
				session_id, query, scope, results_count,
				tokens_returned, tokens_budget, latency_ms, source
			) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
			""",
			(
				session_id,
				query,
				','.join(scope) if scope else None,
				results_count,
				tokens_returned,
				tokens_budget,
				latency_ms,
				source,
			),
		)
		await self.store.db.commit()
