from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import aiosqlite

RETRY_DELAYS_SECONDS = (60, 300, 1800, 7200)


@dataclass(frozen=True)
class QueuedFlush:
	id: int
	session_id: str
	payload: str
	attempts: int
	next_retry: str | None
	error: str | None


class FlushQueue:
	def __init__(self, db: aiosqlite.Connection) -> None:
		self.db = db

	async def enqueue(self, session_id: str, payload: str) -> None:
		await self.db.execute(
			"""
			INSERT INTO flush_queue(session_id, payload, attempts, next_retry, error)
			VALUES (?, ?, 0, ?, NULL)
			ON CONFLICT(session_id) DO UPDATE SET
				payload=excluded.payload,
				attempts=0,
				next_retry=excluded.next_retry,
				error=NULL
			""",
			(session_id, payload, _iso_now()),
		)
		await self.db.commit()

	async def due(self, limit: int = 10) -> list[QueuedFlush]:
		rows = await self.db.execute_fetchall(
			"""
			SELECT id, session_id, payload, attempts, next_retry, error
			FROM flush_queue
			WHERE next_retry IS NULL OR next_retry <= ?
			ORDER BY id
			LIMIT ?
			""",
			(_iso_now(), limit),
		)
		return _to_queued_flushes(rows)

	async def items(self, limit: int = 100) -> list[QueuedFlush]:
		rows = await self.db.execute_fetchall(
			"""
			SELECT id, session_id, payload, attempts, next_retry, error
			FROM flush_queue
			ORDER BY next_retry, id
			LIMIT ?
			""",
			(limit,),
		)
		return _to_queued_flushes(rows)

	async def mark_failed(self, queue_id: int, attempts: int, error: str) -> str:
		next_retry = _retry_at(attempts)
		await self.db.execute(
			"""
			UPDATE flush_queue
			SET attempts=?, next_retry=?, error=?
			WHERE id=?
			""",
			(attempts, next_retry, error, queue_id),
		)
		await self.db.commit()
		return next_retry

	async def complete(self, queue_id: int) -> None:
		await self.db.execute('DELETE FROM flush_queue WHERE id=?', (queue_id,))
		await self.db.commit()

	async def count(self) -> int:
		cursor = await self.db.execute('SELECT COUNT(*) FROM flush_queue')
		row = await cursor.fetchone()
		return int(row[0]) if row else 0


def _to_queued_flushes(rows: Iterable[aiosqlite.Row]) -> list[QueuedFlush]:
	return [
		QueuedFlush(
			id=int(row['id']),
			session_id=str(row['session_id']),
			payload=str(row['payload']),
			attempts=int(row['attempts']),
			next_retry=row['next_retry'],
			error=row['error'],
		)
		for row in rows
	]


def _retry_at(attempts: int) -> str:
	delay_index = min(max(attempts - 1, 0), len(RETRY_DELAYS_SECONDS) - 1)
	next_retry = datetime.now(UTC) + timedelta(seconds=RETRY_DELAYS_SECONDS[delay_index])
	return next_retry.strftime('%Y-%m-%dT%H:%M:%SZ')


def _iso_now() -> str:
	return datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
