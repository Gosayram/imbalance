from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path

import aiosqlite

from imbalance.core.queue import FlushQueue
from imbalance.core.write import machine_id


class SessionStatus(StrEnum):
	ACTIVE = 'active'
	PENDING_FLUSH = 'pending_flush'
	FLUSHED = 'flushed'
	FAILED = 'failed'


@dataclass(frozen=True)
class FlushPayload:
	summary: str
	decisions: list[str]
	next_steps: list[str]

	@classmethod
	def from_json(cls, raw: str) -> FlushPayload:
		try:
			parsed = json.loads(raw)
			if not isinstance(parsed, dict):
				raise TypeError
			summary = parsed['summary']
			decisions = parsed.get('decisions', [])
			next_steps = parsed.get('next_steps', [])
			if (
				not isinstance(summary, str)
				or not summary.strip()
				or not isinstance(decisions, list)
				or not isinstance(next_steps, list)
				or not all(isinstance(item, str) for item in decisions)
				or not all(isinstance(item, str) for item in next_steps)
			):
				raise TypeError
			return cls(
				summary=summary,
				decisions=decisions,
				next_steps=next_steps,
			)
		except (KeyError, TypeError, json.JSONDecodeError) as exc:
			raise ValueError('Invalid pending flush payload') from exc


@dataclass(frozen=True)
class SessionRecord:
	id: str
	kb_name: str
	machine_id: str
	status: SessionStatus
	log_path: str | None


class SessionManager:
	def __init__(self, db: aiosqlite.Connection, kb_name: str, pending_dir: Path) -> None:
		self.db = db
		self.kb_name = kb_name
		self.pending_dir = pending_dir

	async def start(self, session_id: str | None = None) -> SessionRecord:
		final_id = session_id or str(uuid.uuid4())
		host = machine_id()
		await self.db.execute(
			'INSERT INTO sessions(id, kb_name, machine_id, status) VALUES (?, ?, ?, ?)',
			(final_id, self.kb_name, host, SessionStatus.ACTIVE.value),
		)
		await self.db.commit()
		return SessionRecord(final_id, self.kb_name, host, SessionStatus.ACTIVE, None)

	async def prepare_flush(self, session_id: str, payload: FlushPayload) -> Path:
		session = await self.get(session_id)
		if session is None:
			raise KeyError(f'Unknown session: {session_id}')
		if session.status not in {SessionStatus.ACTIVE, SessionStatus.PENDING_FLUSH}:
			raise ValueError(f'Session {session_id} cannot be flushed from {session.status}')

		path = self.pending_dir / f'{session_id}.json'
		_write_atomic_json(path, asdict(payload))
		await self.db.execute(
			'UPDATE sessions SET status=?, log_path=? WHERE id=?',
			(SessionStatus.PENDING_FLUSH.value, str(path), session_id),
		)
		await self.db.commit()
		return path

	async def enqueue_pending(self, session_id: str) -> None:
		session = await self.get(session_id)
		if session is None or session.status != SessionStatus.PENDING_FLUSH or not session.log_path:
			raise ValueError(f'Session {session_id} has no pending flush checkpoint')
		payload = Path(session.log_path).read_text(encoding='utf-8')
		FlushPayload.from_json(payload)
		await FlushQueue(self.db).enqueue(session_id, payload)

	async def mark_flushed(self, session_id: str) -> None:
		session = await self.get(session_id)
		if session is None:
			raise KeyError(f'Unknown session: {session_id}')
		if session.status != SessionStatus.PENDING_FLUSH:
			raise ValueError(f'Session {session_id} cannot be marked flushed from {session.status}')
		await self.db.execute(
			"""
			UPDATE sessions
			SET status=?, flushed_at=strftime('%Y-%m-%dT%H:%M:%SZ','now')
			WHERE id=?
			""",
			(SessionStatus.FLUSHED.value, session_id),
		)
		await self.db.execute('DELETE FROM flush_queue WHERE session_id=?', (session_id,))
		await self.db.commit()
		if session.log_path:
			Path(session.log_path).unlink(missing_ok=True)

	async def recover_pending(self) -> tuple[int, int]:
		rows = await self.db.execute_fetchall(
			'SELECT id, log_path FROM sessions WHERE kb_name=? AND status=?',
			(self.kb_name, SessionStatus.PENDING_FLUSH.value),
		)
		recovered = 0
		failed = 0
		queue = FlushQueue(self.db)
		for row in rows:
			session_id = str(row['id'])
			log_path = row['log_path']
			if log_path and Path(str(log_path)).exists():
				payload = Path(str(log_path)).read_text(encoding='utf-8')
				try:
					FlushPayload.from_json(payload)
				except ValueError:
					await self._mark_failed(session_id)
					failed += 1
				else:
					await queue.enqueue(session_id, payload)
					recovered += 1
			else:
				await self._mark_failed(session_id)
				failed += 1
		return recovered, failed

	async def get(self, session_id: str) -> SessionRecord | None:
		cursor = await self.db.execute(
			'SELECT id, kb_name, machine_id, status, log_path FROM sessions WHERE id=?',
			(session_id,),
		)
		row = await cursor.fetchone()
		if row is None:
			return None
		return SessionRecord(
			id=str(row['id']),
			kb_name=str(row['kb_name']),
			machine_id=str(row['machine_id']),
			status=SessionStatus(str(row['status'])),
			log_path=row['log_path'],
		)

	async def list(self) -> list[SessionRecord]:
		rows = await self.db.execute_fetchall(
			'SELECT id, kb_name, machine_id, status, log_path FROM sessions WHERE kb_name=? '
			'ORDER BY started_at DESC',
			(self.kb_name,),
		)
		return [
			SessionRecord(
				id=str(row['id']),
				kb_name=str(row['kb_name']),
				machine_id=str(row['machine_id']),
				status=SessionStatus(str(row['status'])),
				log_path=row['log_path'],
			)
			for row in rows
		]

	async def _mark_failed(self, session_id: str) -> None:
		await self.db.execute(
			'UPDATE sessions SET status=? WHERE id=?',
			(SessionStatus.FAILED.value, session_id),
		)
		await self.db.execute('DELETE FROM flush_queue WHERE session_id=?', (session_id,))
		await self.db.commit()


def _write_atomic_json(path: Path, payload: dict[str, object]) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	tmp_path = path.with_name(f'.{path.name}.{uuid.uuid4().hex}.tmp')
	try:
		with tmp_path.open('w', encoding='utf-8') as handle:
			json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
			handle.flush()
			os.fsync(handle.fileno())
		os.replace(tmp_path, path)
	finally:
		tmp_path.unlink(missing_ok=True)
