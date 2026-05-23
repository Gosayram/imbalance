from __future__ import annotations

from imbalance.core.context import ContextMode, ContextPack
from imbalance.storage.store import SQLiteStore

PRECEDENCE = [
	'current_task',
	'current_filesystem',
	'session_notes',
	'memory_summary',
	'wiki_sections',
	'archived',
]


class QueryEngine:
	def __init__(
		self, store: SQLiteStore, memory_mode: ContextMode = ContextMode.READ_WRITE
	) -> None:
		self.store = store
		self.memory_mode = memory_mode

	async def get_context_pack(
		self,
		query: str,
		*,
		budget_tokens: int = 2000,
		scope: list[str] | None = None,
	) -> ContextPack:
		summary = None
		summary_budget = min(500, int(budget_tokens * 0.2))
		evidence_budget = budget_tokens

		if self.memory_mode != ContextMode.OFF:
			summary = await self.store.get_memory_summary(max_tokens=summary_budget)
			if summary:
				evidence_budget -= summary_budget

		evidence = await self.store.fts_search(query, limit=8, scope=scope)
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

		return ContextPack(
			query=query,
			budget_tokens=budget_tokens,
			precedence=PRECEDENCE,
			summary=summary,
			evidence=selected,
			omitted=omitted,
			warnings=warnings,
		)
