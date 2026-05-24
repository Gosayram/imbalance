from __future__ import annotations

import logging

import aiosqlite

logger = logging.getLogger(__name__)


async def create_link(
	db: aiosqlite.Connection,
	kb_name: str,
	source_slug: str,
	target_slug: str,
	link_type: str,
) -> None:
	await db.execute(
		"""INSERT INTO kb_links(kb_name, source_slug, target_slug, link_type)
		VALUES (?, ?, ?, ?)
		ON CONFLICT(kb_name, source_slug, target_slug, link_type) DO UPDATE SET
			created_at=strftime('%Y-%m-%dT%H:%M:%SZ','now')""",
		(kb_name, source_slug, target_slug, link_type),
	)
	await db.commit()


async def remove_link(
	db: aiosqlite.Connection,
	kb_name: str,
	source_slug: str,
	target_slug: str,
	link_type: str,
) -> None:
	await db.execute(
		'DELETE FROM kb_links WHERE kb_name=? AND source_slug=? AND target_slug=? AND link_type=?',
		(kb_name, source_slug, target_slug, link_type),
	)
	await db.commit()


async def get_links(
	db: aiosqlite.Connection, kb_name: str, slug: str
) -> list[dict]:
	rows = await db.execute_fetchall(
		'SELECT target_slug, link_type, created_at FROM kb_links '
		'WHERE kb_name=? AND source_slug=? ORDER BY link_type, target_slug',
		(kb_name, slug),
	)
	return [dict(r) for r in rows]


async def expand_links(
	db: aiosqlite.Connection,
	kb_name: str,
	slugs: list[str],
	link_types: tuple[str, ...] = ('references', 'related', 'depends_on'),
	max_related: int = 5,
) -> dict[str, float]:
	if not slugs:
		return {}
	placeholders = ', '.join('?' for _ in slugs)
	type_placeholders = ', '.join('?' for _ in link_types)
	params: list[object] = [kb_name]
	params.extend(slugs)
	params.extend(link_types)

	rows = await db.execute_fetchall(
		f"""SELECT DISTINCT target_slug, link_type
		FROM kb_links
		WHERE kb_name=?
			AND source_slug IN ({placeholders})
			AND link_type IN ({type_placeholders})
			AND target_slug NOT IN ({placeholders})
		LIMIT ?""",
		(*params, *slugs, max_related),
	)
	weights = {'references': 0.7, 'related': 0.5, 'depends_on': 0.6}
	return {r['target_slug']: weights.get(r['link_type'], 0.5) for r in rows}
