import pytest
from unittest.mock import AsyncMock
from imbalance.core.queue import FlushQueue, QueuedFlush, RETRY_DELAYS_SECONDS, _retry_at, _iso_now


@pytest.mark.asyncio
async def test_retry_at():
	result = _retry_at(1)
	assert result is not None


@pytest.mark.asyncio
async def test_iso_now():
	result = _iso_now()
	assert result is not None


@pytest.mark.asyncio
async def test_queued_flush():
	flush = QueuedFlush(id=1, session_id="sess", payload="{}", attempts=0, next_retry=None, error=None)
	assert flush.id == 1


@pytest.mark.asyncio
async def test_flush_queue_enqueue():
	db = AsyncMock()
	queue = FlushQueue(db)
	await queue.enqueue("sess", "{}")
	db.execute.assert_called()


@pytest.mark.asyncio
async def test_flush_queue_due():
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[])
	queue = FlushQueue(db)
	results = await queue.due()
	assert results == []


@pytest.mark.asyncio
async def test_flush_queue_count():
	db = AsyncMock()
	cursor = AsyncMock()
	cursor.fetchone = AsyncMock(return_value=[5])
	db.execute = AsyncMock(return_value=cursor)
	queue = FlushQueue(db)
	count = await queue.count()
	assert count == 5
