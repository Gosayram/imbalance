from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import aiosqlite

logger = logging.getLogger(__name__)

CONFLICT_PROMPT = """New decision: {new}

Existing decisions in same area:
{existing}

Do any existing decisions contradict the new one?
Return JSON only: {{"conflict": bool, "conflicting_slug": str or null, "reason": str or null}}
"""


@dataclass(frozen=True)
class ConflictResult:
	conflict: bool
	conflicting_slug: str | None = None
	reason: str | None = None


async def detect_conflict(
	db: aiosqlite.Connection,
	kb_name: str,
	new_slug: str,
	new_content: str,
	router=None,
) -> ConflictResult:
	rows = await db.execute_fetchall(
		'SELECT slug, content FROM wiki_sections '
		'WHERE kb_name=? AND section=? AND archived=FALSE AND slug != ?',
		(kb_name, 'decisions', new_slug),
	)
	if not rows:
		return ConflictResult(conflict=False)

	if router is None:
		return ConflictResult(conflict=False)

	existing_text = '\n'.join(f'- [{r["slug"]}]: {r["content"][:200]}' for r in rows[:10])

	try:
		response = await router.complete(
			CONFLICT_PROMPT.format(new=new_content[:500], existing=existing_text),
			max_tokens=200,
		)
		parsed = json.loads(response)
		return ConflictResult(
			conflict=bool(parsed.get('conflict')),
			conflicting_slug=parsed.get('conflicting_slug'),
			reason=parsed.get('reason'),
		)
	except (json.JSONDecodeError, KeyError, TypeError):
		logger.warning('Conflict detection failed to parse LLM response')
		return ConflictResult(conflict=False)
	except Exception as exc:
		logger.warning('Conflict detection error: %s', exc)
		return ConflictResult(conflict=False)


async def mark_conflict(
	db: aiosqlite.Connection,
	kb_name: str,
	slug_a: str,
	slug_b: str,
	reason: str | None = None,
) -> None:
	await db.execute(
		"""INSERT INTO kb_links(kb_name, source_slug, target_slug, link_type)
		VALUES (?, ?, ?, 'conflicts')
		ON CONFLICT(kb_name, source_slug, target_slug, link_type) DO UPDATE SET
			created_at=strftime('%Y-%m-%dT%H:%M:%SZ','now')""",
		(kb_name, slug_a, slug_b),
	)
	await db.execute(
		"""INSERT INTO kb_links(kb_name, source_slug, target_slug, link_type)
		VALUES (?, ?, ?, 'conflicts')
		ON CONFLICT(kb_name, source_slug, target_slug, link_type) DO UPDATE SET
			created_at=strftime('%Y-%m-%dT%H:%M:%SZ','now')""",
		(kb_name, slug_b, slug_a),
	)
	await db.commit()


async def get_conflicts(db: aiosqlite.Connection, kb_name: str) -> list[dict]:
	rows = await db.execute_fetchall(
		"SELECT source_slug, target_slug, created_at FROM kb_links "
		"WHERE kb_name=? AND link_type='conflicts' ORDER BY created_at DESC",
		(kb_name,),
	)
	return [dict(r) for r in rows]
