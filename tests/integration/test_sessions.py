from pathlib import Path

import pytest

from imbalance.core.queue import FlushQueue
from imbalance.core.session import FlushPayload, SessionManager, SessionStatus
from imbalance.storage.db import open_db, run_migrations


@pytest.mark.asyncio
async def test_checkpoint_is_queued_and_removed_after_flush(tmp_path: Path) -> None:
	db = await open_db(tmp_path / 'kb.db')
	await run_migrations(db)
	manager = SessionManager(db, 'test-kb', tmp_path / 'pending')
	session = await manager.start('s1')

	path = await manager.prepare_flush(
		session.id,
		FlushPayload(summary='Done.', decisions=['SQLite WAL'], next_steps=['Tests']),
	)
	await manager.enqueue_pending(session.id)

	assert path.exists()
	pending = await manager.get(session.id)
	assert pending is not None
	assert pending.status == SessionStatus.PENDING_FLUSH
	assert await FlushQueue(db).count() == 1

	await manager.mark_flushed(session.id)

	assert not path.exists()
	flushed = await manager.get(session.id)
	assert flushed is not None
	assert flushed.status == SessionStatus.FLUSHED
	assert await FlushQueue(db).count() == 0
	await db.close()


@pytest.mark.asyncio
async def test_active_session_cannot_be_marked_flushed_without_checkpoint(tmp_path: Path) -> None:
	db = await open_db(tmp_path / 'kb.db')
	await run_migrations(db)
	manager = SessionManager(db, 'test-kb', tmp_path / 'pending')
	await manager.start('active')

	with pytest.raises(ValueError, match='cannot be marked flushed'):
		await manager.mark_flushed('active')

	await db.close()


@pytest.mark.asyncio
async def test_recovery_enqueues_valid_pending_and_fails_corrupt_payload(tmp_path: Path) -> None:
	db = await open_db(tmp_path / 'kb.db')
	await run_migrations(db)
	manager = SessionManager(db, 'test-kb', tmp_path / 'pending')

	await manager.start('valid')
	await manager.prepare_flush('valid', FlushPayload('Summary', [], []))
	await manager.start('broken')
	broken_path = await manager.prepare_flush('broken', FlushPayload('Summary', [], []))
	await manager.enqueue_pending('broken')
	broken_path.write_text('{invalid', encoding='utf-8')

	recovered, failed = await manager.recover_pending()

	assert (recovered, failed) == (1, 1)
	assert await FlushQueue(db).count() == 1
	broken = await manager.get('broken')
	assert broken is not None
	assert broken.status == SessionStatus.FAILED
	await db.close()


@pytest.mark.asyncio
async def test_queue_failure_schedules_retry(tmp_path: Path) -> None:
	db = await open_db(tmp_path / 'kb.db')
	await run_migrations(db)
	manager = SessionManager(db, 'test-kb', tmp_path / 'pending')
	await manager.start('s1')
	await manager.prepare_flush('s1', FlushPayload('Summary', [], []))
	await manager.enqueue_pending('s1')
	queue = FlushQueue(db)
	item = (await queue.due())[0]

	next_retry = await queue.mark_failed(item.id, attempts=1, error='provider down')
	row = await db.execute_fetchall(
		'SELECT attempts, next_retry, error FROM flush_queue WHERE id=?', (item.id,)
	)

	assert row[0]['attempts'] == 1
	assert row[0]['next_retry'] == next_retry
	assert row[0]['error'] == 'provider down'
	items = await queue.items()
	assert [item.session_id for item in items] == ['s1']
	await db.close()


def test_flush_payload_rejects_invalid_shape() -> None:
	with pytest.raises(ValueError, match='Invalid pending flush payload'):
		FlushPayload.from_json('{"summary": "Done", "decisions": "not-a-list"}')
