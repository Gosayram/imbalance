from __future__ import annotations

import logging
from dataclasses import dataclass

from imbalance.core.router import ModelRouter
from imbalance.storage.store import SQLiteStore

logger = logging.getLogger(__name__)

CONSOLIDATE_MEMORY_PROMPT = """\
You are consolidating raw observations into a concise project memory summary.

Current summary:
{current_summary}

New raw observations:
{raw_memories}

Produce an updated summary that:
1. Merges new facts into the existing summary
2. Removes contradictions (keep the newer info)
3. Stays under ~500 tokens
4. Each line should reference its source (session_id or slug)

Return ONLY the updated summary text, nothing else.
"""


@dataclass(frozen=True)
class ConsolidationResult:
	updated: bool
	summary: str | None = None
	memories_consumed: int = 0


async def consolidate_raw_memories(
	store: SQLiteStore,
	router: ModelRouter,
	max_summary_tokens: int = 500,
	batch_limit: int = 128,
) -> ConsolidationResult:
	raw = await store.fetch_unconsumed_raw_memories(limit=batch_limit)
	if not raw:
		return ConsolidationResult(updated=False)

	raw_ids = [int(r['id']) for r in raw]
	current_summary = await store.get_memory_summary(max_tokens=max_summary_tokens) or ''

	formatted = '\n'.join(
		f"- [{r['memory_type']}] (conf={r['confidence']:.2f}, session={r['session_id'][:8]}...) {r['content']}"
		for r in raw
	)

	prompt = CONSOLIDATE_MEMORY_PROMPT.format(
		current_summary=current_summary or '(empty)',
		raw_memories=formatted,
	)

	try:
		new_summary = await router.complete(prompt, max_tokens=max_summary_tokens)
	except Exception:
		logger.exception('Memory consolidation failed')
		return ConsolidationResult(updated=False)

	token_count = len(new_summary.split())
	await store.upsert_memory_summary(new_summary, token_count)
	await store.mark_raw_memories_consumed(raw_ids)

	logger.info(f'Consolidated {len(raw_ids)} raw memories into summary ({token_count} tokens)')
	return ConsolidationResult(
		updated=True,
		summary=new_summary,
		memories_consumed=len(raw_ids),
	)
