import json

import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path
from imbalance.core.session import SessionStatus, FlushPayload, SessionRecord, SessionManager


def test_session_status_values():
	assert SessionStatus.ACTIVE == "active"
	assert SessionStatus.PENDING_FLUSH == "pending_flush"
	assert SessionStatus.FLUSHED == "flushed"
	assert SessionStatus.FAILED == "failed"


def test_flush_payload_from_json():
	payload = FlushPayload.from_json('{"summary": "test", "decisions": ["a"], "next_steps": ["b"]}')
	assert payload.summary == "test"
	assert payload.decisions == ["a"]
	assert payload.next_steps == ["b"]


def test_flush_payload_from_json_defaults():
	payload = FlushPayload.from_json('{"summary": "test"}')
	assert payload.summary == "test"
	assert payload.decisions == []
	assert payload.next_steps == []


def test_flush_payload_from_json_invalid():
	with pytest.raises(Exception):
		FlushPayload.from_json('not json')


def test_flush_payload_from_json_missing_summary():
	with pytest.raises(Exception):
		FlushPayload.from_json('{"decisions": []}')


def test_flush_payload_from_json_invalid_decisions():
	with pytest.raises(Exception):
		FlushPayload.from_json('{"summary": "test", "decisions": "not a list"}')


@pytest.mark.asyncio
async def test_session_manager_start():
	db = AsyncMock()
	db.execute = AsyncMock()
	db.commit = AsyncMock()
	manager = SessionManager(db, "test_kb", Path("/tmp/pending"))
	record = await manager.start()
	assert record.kb_name == "test_kb"
	assert record.status == SessionStatus.ACTIVE


@pytest.mark.asyncio
async def test_session_manager_get_not_found():
	db = AsyncMock()
	cursor = AsyncMock()
	cursor.fetchone = AsyncMock(return_value=None)
	db.execute = AsyncMock(return_value=cursor)
	manager = SessionManager(db, "test_kb", Path("/tmp/pending"))
	result = await manager.get("nonexistent")
	assert result is None


@pytest.mark.asyncio
async def test_session_manager_get_found():
	db = AsyncMock()
	cursor = AsyncMock()
	cursor.fetchone = AsyncMock(return_value={
		'id': 'test-id', 'kb_name': 'test_kb', 'machine_id': 'host1',
		'status': 'active', 'log_path': None
	})
	db.execute = AsyncMock(return_value=cursor)
	manager = SessionManager(db, "test_kb", Path("/tmp/pending"))
	result = await manager.get("test-id")
	assert result is not None
	assert result.id == "test-id"