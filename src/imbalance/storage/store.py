from __future__ import annotations

from collections.abc import Iterable

import aiosqlite

from imbalance.core.context import ContextChunk


class SQLiteStore:
	def __init__(self, db: aiosqlite.Connection, kb_name: str) -> None:
		self.db = db
		self.kb_name = kb_name

	async def upsert_section(
		self,
		*,
		slug: str,
		section: str,
		content: str,
		token_count: int,
		session_id: str | None = None,
		machine_id: str | None = None,
		tags: Iterable[str] = (),
	) -> int:
		try:
			existing = await self._fetchone(
				'SELECT id, content FROM wiki_sections WHERE kb_name=? AND slug=?',
				(self.kb_name, slug),
			)
			change_type = 'update' if existing else 'create'

			await self.db.execute(
				"""
				INSERT INTO wiki_sections(
					kb_name, section, slug, content, token_count, session_id, machine_id
				)
				VALUES (?, ?, ?, ?, ?, ?, ?)
				ON CONFLICT(kb_name, slug) DO UPDATE SET
					section=excluded.section,
					content=excluded.content,
					token_count=excluded.token_count,
					session_id=excluded.session_id,
					machine_id=excluded.machine_id,
					updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now')
				""",
				(self.kb_name, section, slug, content, token_count, session_id, machine_id),
			)
			row = await self._fetchone(
				'SELECT id FROM wiki_sections WHERE kb_name=? AND slug=?',
				(self.kb_name, slug),
			)
			if row is None:
				raise RuntimeError(f'Section upsert did not produce a row for {slug}')
			section_id = int(row['id'])

			await self.db.execute(
				"""
				INSERT INTO wiki_history(kb_name, slug, content, changed_by, change_type)
				VALUES (?, ?, ?, ?, ?)
				""",
				(self.kb_name, slug, content, session_id, change_type),
			)
			await self.db.execute('DELETE FROM wiki_tags WHERE section_id=?', (section_id,))
			await self.db.executemany(
				'INSERT OR IGNORE INTO wiki_tags(section_id, tag) VALUES (?, ?)',
				[(section_id, tag) for tag in tags],
			)
			await self.db.commit()
			return section_id
		except Exception:
			await self.db.rollback()
			raise

	async def fts_search(
		self,
		query: str,
		*,
		limit: int = 8,
		scope: list[str] | None = None,
	) -> list[ContextChunk]:
		if limit < 1:
			limit = 1
		params: list[object] = [self.kb_name, query]
		scope_sql = ''
		if scope:
			placeholders = ', '.join('?' for _ in scope)
			scope_sql = f'AND ws.section IN ({placeholders})'
			params.extend(scope)
		params.append(limit)

		rows = await self.db.execute_fetchall(
			f"""
			SELECT
				ws.slug,
				ws.section,
				ws.content,
				ws.token_count,
				ws.confirmation_count,
				bm25(wiki_fts) AS score
			FROM wiki_fts
			JOIN wiki_sections ws ON ws.id = wiki_fts.rowid
			WHERE ws.kb_name = ?
				AND wiki_fts MATCH ?
				AND ws.archived = FALSE
				{scope_sql}
			ORDER BY score
			LIMIT ?
			""",
			params,
		)
		return [
			ContextChunk(
				slug=row['slug'],
				section=row['section'],
				content=row['content'],
				score=float(row['score']),
				token_count=int(row['token_count']),
				confidence=min(float(row['confirmation_count']) / 10.0, 1.0),
			)
			for row in rows
		]

	async def get_memory_summary(self, max_tokens: int) -> str | None:
		row = await self._fetchone(
			'SELECT content, token_count FROM memory_summary WHERE kb_name=?',
			(self.kb_name,),
		)
		if row is None:
			return None
		content = str(row['content'])
		if int(row['token_count']) <= max_tokens:
			return content
		return _truncate_words(content, max_tokens)

	async def upsert_memory_summary(self, content: str, token_count: int) -> None:
		try:
			await self.db.execute(
				"""
				INSERT INTO memory_summary(kb_name, content, token_count)
				VALUES (?, ?, ?)
				ON CONFLICT(kb_name) DO UPDATE SET
					content=excluded.content,
					token_count=excluded.token_count,
					updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now')
				""",
				(self.kb_name, content, token_count),
			)
			await self.db.commit()
		except Exception:
			await self.db.rollback()
			raise

	async def _fetchone(self, sql: str, params: tuple[object, ...]) -> aiosqlite.Row | None:
		cursor = await self.db.execute(sql, params)
		return await cursor.fetchone()


def _truncate_words(content: str, approx_tokens: int) -> str:
	words = content.split()
	if len(words) <= approx_tokens:
		return content
	return ' '.join(words[:approx_tokens])
