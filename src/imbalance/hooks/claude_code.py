from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HookResult:
	"""Result of a Claude Code hook execution."""
	inject: str | None = None
	block: bool = False
	reason: str | None = None


async def get_active_session(db: aiosqlite.Connection) -> dict[str, Any] | None:
	"""Get the most recent active session."""
	rows = await db.execute_fetchall(
		"SELECT * FROM sessions WHERE status = 'active' ORDER BY started_at DESC LIMIT 1"
	)
	if not rows:
		return None
	return dict(rows[0])


async def hook_session_start(db: aiosqlite.Connection, kb_name: str) -> HookResult:
	"""Called when a Claude Code session starts."""
	logger.info(f'Session started for KB: {kb_name}')
	return HookResult(inject=None)


async def hook_session_stop(db: aiosqlite.Connection, kb_name: str, auto_flush: bool = True) -> HookResult:
	"""Called when a Claude Code session stops."""
	logger.info(f'Session stopped for KB: {kb_name}, auto_flush={auto_flush}')
	return HookResult(inject=None)


async def hook_prompt_submit(
	db: aiosqlite.Connection,
	budget_threshold: float = 0.85,
) -> HookResult:
	"""
	Called when a user prompt is submitted.
	Checks context budget and injects warning if needed.
	"""
	session = await get_active_session(db)
	if not session:
		return HookResult(inject=None)

	# Estimate usage based on session data
	# This is a simplified check - in production you'd track actual token usage
	rows = await db.execute_fetchall(
		"SELECT SUM(token_count) as total FROM wiki_sections WHERE kb_name = ?",
		(session.get('kb_name', ''),),
	)
	total_tokens = rows[0]['total'] if rows and rows[0]['total'] else 0
	budget = 2000  # Default budget

	if total_tokens > 0:
		ratio = total_tokens / budget
		if ratio >= budget_threshold:
			return HookResult(
				inject=(
					f'[imbalance] Context at {ratio:.0%}. '
					f'Call save_fact() for any key findings now.'
				)
			)

	return HookResult(inject=None)
