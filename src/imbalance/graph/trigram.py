from __future__ import annotations

import logging
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)


def _extract_trigrams(name: str) -> frozenset[str]:
	if len(name) < 3:
		return frozenset()
	return frozenset(name[i : i + 3].lower() for i in range(len(name) - 2))


async def trigram_search(
	db: aiosqlite.Connection,
	query: str,
	kb_name: str,
	limit: int = 20,
) -> list[dict[str, Any]]:
	if len(query) < 2:
		return []

	trigrams = _extract_trigrams(query)
	if not trigrams:
		return []

	placeholders = ','.join('?' * len(trigrams))
	rows = await db.execute_fetchall(
		f"""
		SELECT DISTINCT s.id, s.name, s.kind, s.file_path, s.line
		FROM code_symbols s
		JOIN trigram_index t ON s.id = t.rowid
		WHERE s.kb_name = ? AND t.trigram IN ({placeholders})
		ORDER BY s.name
		LIMIT ?
		""",
		(kb_name, *trigrams, limit),
	)
	return [dict(r) for r in rows]


async def build_trigram_index(
	db: aiosqlite.Connection,
	symbol_ids: dict[str, int],
) -> int:
	inserted = 0
	batch: list[tuple[str, int]] = []
	seen: set[tuple[str, int]] = set()

	for name, sym_id in symbol_ids.items():
		for trigram in _extract_trigrams(name):
			pair = (trigram, sym_id)
			if pair not in seen:
				seen.add(pair)
				batch.append(pair)

		if len(batch) >= 50_000:
			n = len(batch)
			await db.executemany('INSERT OR IGNORE INTO trigram_index VALUES (?,?)', batch)
			await db.commit()
			batch.clear()
			inserted += n

	if batch:
		await db.executemany('INSERT OR IGNORE INTO trigram_index VALUES (?,?)', batch)
		await db.commit()
		inserted += len(batch)

	del seen
	return inserted
