from __future__ import annotations

from imbalance.core.context import ContextChunk, ContextPack
from imbalance.core.query import QueryEngine


class MultiKBQuery:
	def __init__(
		self,
		primary: QueryEngine,
		inherited: QueryEngine | None = None,
		inherit_weight: float = 0.5,
	) -> None:
		self._primary = primary
		self._inherited = inherited
		self._inherit_weight = inherit_weight

	async def get_context_pack(
		self,
		query: str,
		*,
		budget_tokens: int = 2000,
		scope: list[str] | None = None,
		session_id: str | None = None,
		tags: list[str] | None = None,
	) -> ContextPack:
		primary_pack = await self._primary.get_context_pack(
			query,
			budget_tokens=budget_tokens,
			scope=scope,
			session_id=session_id,
			tags=tags,
		)

		if self._inherited is None:
			return primary_pack

		inherit_budget = int(budget_tokens * self._inherit_weight)
		inherit_pack = await self._inherited.get_context_pack(
			query,
			budget_tokens=inherit_budget,
			scope=scope,
			tags=tags,
		)

		merged_evidence = list(primary_pack.evidence)
		seen = {c.slug for c in merged_evidence}
		for chunk in inherit_pack.evidence:
			if chunk.slug not in seen:
				scaled = ContextChunk(
					slug=chunk.slug,
					section=chunk.section,
					content=chunk.content,
					score=chunk.score * self._inherit_weight,
					token_count=chunk.token_count,
					confidence=chunk.confidence,
				)
				merged_evidence.append(scaled)
				seen.add(chunk.slug)

		all_warnings = list(primary_pack.warnings)
		if inherit_pack.summary:
			all_warnings.append(f'[inherited] {inherit_pack.summary[:100]}')

		return ContextPack(
			query=query,
			budget_tokens=budget_tokens,
			precedence=primary_pack.precedence,
			summary=primary_pack.summary,
			evidence=merged_evidence,
			omitted=primary_pack.omitted + inherit_pack.omitted,
			warnings=all_warnings,
		)
