from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import aiosqlite

from imbalance.core.tokens import estimate_tokens

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BatchResult:
	"""Result of batch operation."""
	total: int
	success: int
	failed: int
	errors: list[str]


async def batch_upsert_sections(
	db: aiosqlite.Connection,
	kb_name: str,
	sections: list[dict[str, Any]],
	batch_size: int = 100,
) -> BatchResult:
	"""Batch upsert wiki sections.

	Args:
		db: Database connection
		kb_name: Knowledge base name
		sections: List of section dicts with keys: slug, section, content, tags
		batch_size: Number of sections per batch

	Returns:
		BatchResult with counts
	"""
	total = len(sections)
	success = 0
	failed = 0
	errors: list[str] = []

	for i in range(0, total, batch_size):
		batch = sections[i:i + batch_size]
		try:
			await db.executemany(
				"""INSERT INTO wiki_sections (kb_name, section, slug, content, token_count, updated_at)
				VALUES (?, ?, ?, ?, ?, datetime('now'))
				ON CONFLICT(kb_name, slug) DO UPDATE SET
					content=excluded.content,
					token_count=excluded.token_count,
					updated_at=excluded.updated_at""",
				[
					(
						kb_name,
						s['section'],
						s['slug'],
						s['content'],
						estimate_tokens(s['content']),
					)
					for s in batch
				],
			)
			await db.commit()
			success += len(batch)
			logger.info(f'Batch upserted {len(batch)} sections')
		except Exception as e:
			failed += len(batch)
			error_msg = f'Batch error at offset {i}: {e}'
			errors.append(error_msg)
			logger.error(error_msg)

	return BatchResult(total=total, success=success, failed=failed, errors=errors)


async def batch_create_links(
	db: aiosqlite.Connection,
	kb_name: str,
	links: list[dict[str, str]],
	batch_size: int = 100,
) -> BatchResult:
	"""Batch create KB links.

	Args:
		db: Database connection
		kb_name: Knowledge base name
		links: List of link dicts with keys: source_slug, target_slug, link_type
		batch_size: Number of links per batch

	Returns:
		BatchResult with counts
	"""
	total = len(links)
	success = 0
	failed = 0
	errors: list[str] = []

	for i in range(0, total, batch_size):
		batch = links[i:i + batch_size]
		try:
			await db.executemany(
				"""INSERT OR IGNORE INTO kb_links (kb_name, source_slug, target_slug, link_type)
				VALUES (?, ?, ?, ?)""",
				[
					(kb_name, lnk['source_slug'], lnk['target_slug'], lnk['link_type'])
					for lnk in batch
				],
			)
			await db.commit()
			success += len(batch)
			logger.info(f'Batch created {len(batch)} links')
		except Exception as e:
			failed += len(batch)
			error_msg = f'Batch error at offset {i}: {e}'
			errors.append(error_msg)
			logger.error(error_msg)

	return BatchResult(total=total, success=success, failed=failed, errors=errors)


async def batch_archive_sections(
	db: aiosqlite.Connection,
	kb_name: str,
	slugs: list[str],
	reason: str = '',
	batch_size: int = 100,
) -> BatchResult:
	"""Batch archive wiki sections.

	Args:
		db: Database connection
		kb_name: Knowledge base name
		slugs: List of section slugs to archive
		reason: Archive reason
		batch_size: Number of sections per batch

	Returns:
		BatchResult with counts
	"""
	total = len(slugs)
	success = 0
	failed = 0
	errors: list[str] = []

	for i in range(0, total, batch_size):
		batch = slugs[i:i + batch_size]
		try:
			await db.executemany(
				"""UPDATE wiki_sections
				SET archived=TRUE, archived_at=datetime('now'), archive_reason=?
				WHERE kb_name=? AND slug=? AND archived=FALSE""",
				[(reason, kb_name, slug) for slug in batch],
			)
			await db.commit()
			success += len(batch)
			logger.info(f'Batch archived {len(batch)} sections')
		except Exception as e:
			failed += len(batch)
			error_msg = f'Batch error at offset {i}: {e}'
			errors.append(error_msg)
			logger.error(error_msg)

	return BatchResult(total=total, success=success, failed=failed, errors=errors)
