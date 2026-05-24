from __future__ import annotations

import json
import logging
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

_VEC_AVAILABLE: bool | None = None


async def is_vec_available(db: aiosqlite.Connection) -> bool:
	global _VEC_AVAILABLE
	if _VEC_AVAILABLE is not None:
		return _VEC_AVAILABLE
	try:
		import sqlite_vec

		await db.enable_load_extension(True)
		sqlite_vec.load(db.conn)
		await db.enable_load_extension(False)
		_VEC_AVAILABLE = True
		logger.info('sqlite-vec extension loaded')
	except Exception:
		_VEC_AVAILABLE = False
		logger.debug('sqlite-vec not available, using FTS5-only mode')
	return _VEC_AVAILABLE


async def ensure_vec_table(db: aiosqlite.Connection, dimension: int = 768) -> bool:
	if not await is_vec_available(db):
		return False
	await db.execute(
		f'CREATE VIRTUAL TABLE IF NOT EXISTS wiki_vec USING vec0('
		f'  embedding float[{dimension}]'
		f')'
	)
	await db.commit()
	return True


async def upsert_embedding(
	db: aiosqlite.Connection,
	section_id: int,
	embedding: list[float],
) -> None:
	emb_blob = _floats_to_blob(embedding)
	await db.execute(
		"DELETE FROM wiki_vec WHERE rowid = ?", (section_id,)
	)
	await db.execute(
		"INSERT INTO wiki_vec(rowid, embedding) VALUES (?, ?)",
		(section_id, emb_blob),
	)
	await db.commit()


async def search_by_embedding(
	db: aiosqlite.Connection,
	embedding: list[float],
	limit: int = 8,
) -> list[dict[str, Any]]:
	emb_blob = _floats_to_blob(embedding)
	rows = await db.execute_fetchall(
		"""
		SELECT v.rowid as section_id, v.distance
		FROM wiki_vec v
		WHERE v.embedding MATCH ?
		ORDER BY v.distance
		LIMIT ?
		""",
		(json.dumps([emb_blob]), limit),
	)
	return [
		{'section_id': dict(r)['section_id'], 'distance': dict(r)['distance']}
		for r in rows
	]


async def delete_embedding(db: aiosqlite.Connection, section_id: int) -> None:
	await db.execute("DELETE FROM wiki_vec WHERE rowid = ?", (section_id,))
	await db.commit()


def _floats_to_blob(embedding: list[float]) -> bytes:
	import struct

	return struct.pack(f'{len(embedding)}f', *embedding)


def reset_cache() -> None:
	global _VEC_AVAILABLE
	_VEC_AVAILABLE = None
