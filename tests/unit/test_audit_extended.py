import pytest
from unittest.mock import AsyncMock
from imbalance.core.audit import AuditLogger, AuditAction, ensure_audit_table


@pytest.mark.asyncio
async def test_audit_log_create():
	db = AsyncMock()
	db.execute = AsyncMock()
	db.commit = AsyncMock()

	logger = AuditLogger(db, 'test-kb')
	await logger.log(
		action=AuditAction.CREATE,
		resource_type='wiki_section',
		resource_id='decisions/001-db',
	)

	db.execute.assert_called_once()
	db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_audit_log_update():
	db = AsyncMock()
	db.execute = AsyncMock()
	db.commit = AsyncMock()

	logger = AuditLogger(db, 'test-kb')
	await logger.log(
		action=AuditAction.UPDATE,
		resource_type='wiki_section',
		resource_id='decisions/001-db',
		details={'old': 'old content', 'new': 'new content'},
	)

	db.execute.assert_called_once()
	db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_audit_log_delete():
	db = AsyncMock()
	db.execute = AsyncMock()
	db.commit = AsyncMock()

	logger = AuditLogger(db, 'test-kb')
	await logger.log(
		action=AuditAction.DELETE,
		resource_type='wiki_section',
		resource_id='decisions/001-db',
	)

	db.execute.assert_called_once()
	db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_audit_log_with_all_params():
	db = AsyncMock()
	db.execute = AsyncMock()
	db.commit = AsyncMock()

	logger = AuditLogger(db, 'test-kb')
	await logger.log(
		action=AuditAction.FLUSH,
		resource_type='session',
		resource_id='session-123',
		details={'summary': 'test'},
		user_id='user-456',
		session_id='session-789',
	)

	db.execute.assert_called_once()
	db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_audit_get_logs_empty():
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[])

	logger = AuditLogger(db, 'test-kb')
	logs = await logger.get_logs()

	assert logs == []


@pytest.mark.asyncio
async def test_audit_get_logs_with_filters():
	mock_row = {
		'id': 1,
		'kb_name': 'test-kb',
		'action': 'create',
		'resource_type': 'wiki_section',
		'resource_id': 'decisions/001-db',
		'details': None,
		'user_id': None,
		'session_id': None,
		'timestamp': '2026-05-29T12:00:00Z',
	}
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[mock_row])

	logger = AuditLogger(db, 'test-kb')
	logs = await logger.get_logs(resource_type='wiki_section', action=AuditAction.CREATE)

	assert len(logs) == 1
	assert logs[0]['action'] == 'create'


@pytest.mark.asyncio
async def test_ensure_audit_table():
	db = AsyncMock()
	db.execute = AsyncMock()
	db.commit = AsyncMock()

	await ensure_audit_table(db)

	assert db.execute.call_count == 2
	db.commit.assert_called_once()


def test_audit_action_enum():
	assert AuditAction.CREATE == 'create'
	assert AuditAction.UPDATE == 'update'
	assert AuditAction.DELETE == 'delete'
	assert AuditAction.ARCHIVE == 'archive'
	assert AuditAction.RESTORE == 'restore'
	assert AuditAction.IMPORT == 'import'
	assert AuditAction.EXPORT == 'export'
	assert AuditAction.FLUSH == 'flush'
	assert AuditAction.COMPACT == 'compact'


def test_audit_action_str():
	assert str(AuditAction.CREATE) == 'create'
	assert str(AuditAction.UPDATE) == 'update'
