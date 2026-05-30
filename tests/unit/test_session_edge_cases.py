import pytest
from unittest.mock import AsyncMock, MagicMock
from imbalance.core.session import SessionManager, SessionRecord, FlushPayload, SessionStatus


def test_session_record_init():
	session = SessionRecord(
		id='test-id',
		kb_name='test-kb',
		machine_id='test-machine',
		status=SessionStatus.ACTIVE,
		log_path=None,
	)
	assert session.id == 'test-id'
	assert session.kb_name == 'test-kb'
	assert session.machine_id == 'test-machine'
	assert session.status == SessionStatus.ACTIVE
	assert session.log_path is None


def test_session_record_with_log_path():
	session = SessionRecord(
		id='test-id',
		kb_name='test-kb',
		machine_id='test-machine',
		status=SessionStatus.PENDING_FLUSH,
		log_path='/tmp/test.json',
	)
	assert session.log_path == '/tmp/test.json'


def test_flush_payload_init():
	payload = FlushPayload(
		summary='test summary',
		decisions=['decision1', 'decision2'],
		next_steps=['step1', 'step2'],
	)
	assert payload.summary == 'test summary'
	assert len(payload.decisions) == 2
	assert len(payload.next_steps) == 2


def test_flush_payload_empty():
	payload = FlushPayload(
		summary='test summary',
		decisions=[],
		next_steps=[],
	)
	assert payload.decisions == []
	assert payload.next_steps == []


def test_flush_payload_from_json():
	json_str = '{"summary": "test", "decisions": ["d1"], "next_steps": ["s1"]}'
	payload = FlushPayload.from_json(json_str)
	assert payload.summary == 'test'
	assert payload.decisions == ['d1']
	assert payload.next_steps == ['s1']


def test_flush_payload_from_json_invalid():
	with pytest.raises(ValueError):
		FlushPayload.from_json('invalid json')


def test_session_status_values():
	assert SessionStatus.ACTIVE == 'active'
	assert SessionStatus.PENDING_FLUSH == 'pending_flush'
	assert SessionStatus.FLUSHED == 'flushed'
	assert SessionStatus.FAILED == 'failed'


@pytest.mark.asyncio
async def test_session_manager_start():
	db = AsyncMock()
	db.execute = AsyncMock()
	db.commit = AsyncMock()

	manager = SessionManager(db, 'test-kb', MagicMock())
	session = await manager.start()

	assert session.kb_name == 'test-kb'
	assert session.status == SessionStatus.ACTIVE


@pytest.mark.asyncio
async def test_session_manager_list():
	mock_row = {
		'id': 'test-id',
		'kb_name': 'test-kb',
		'machine_id': 'test-machine',
		'status': 'active',
		'log_path': None,
	}
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[mock_row])

	manager = SessionManager(db, 'test-kb', MagicMock())
	sessions = await manager.list()

	assert len(sessions) == 1
	assert sessions[0].id == 'test-id'


@pytest.mark.asyncio
async def test_session_manager_list_empty():
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[])

	manager = SessionManager(db, 'test-kb', MagicMock())
	sessions = await manager.list()

	assert len(sessions) == 0
