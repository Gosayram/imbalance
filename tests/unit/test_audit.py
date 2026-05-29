import pytest
from unittest.mock import AsyncMock, MagicMock
from imbalance.core.audit import AuditLogger, AuditAction, ensure_audit_table


@pytest.mark.asyncio
async def test_audit_log():
	db = AsyncMock()
	db.execute = AsyncMock()
	db.commit = AsyncMock()

	logger = AuditLogger(db, 'test-kb')
	await logger.log(
		action=AuditAction.CREATE,
		resource_type='wiki_section',
		resource_id='decisions/001-db',
		details={'content': 'test'},
	)

	db.execute.assert_called_once()
	db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_audit_log_with_session():
	db = AsyncMock()
	db.execute = AsyncMock()
	db.commit = AsyncMock()

	logger = AuditLogger(db, 'test-kb')
	await logger.log(
		action=AuditAction.UPDATE,
		resource_type='wiki_section',
		resource_id='decisions/001-db',
		session_id='session-123',
	)

	db.execute.assert_called_once()
	db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_audit_get_logs():
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
	logs = await logger.get_logs(resource_type='wiki_section')

	assert len(logs) == 1
	assert logs[0]['action'] == 'create'


@pytest.mark.asyncio
async def test_ensure_audit_table():
	db = AsyncMock()
	db.execute = AsyncMock()
	db.commit = AsyncMock()

	await ensure_audit_table(db)

	assert db.execute.call_count == 2  # CREATE TABLE + CREATE INDEX
	db.commit.assert_called_once()


def test_audit_action_values():
	assert AuditAction.CREATE == 'create'
	assert AuditAction.UPDATE == 'update'
	assert AuditAction.DELETE == 'delete'
	assert AuditAction.ARCHIVE == 'archive'
	assert AuditAction.RESTORE == 'restore'
	assert AuditAction.IMPORT == 'import'
	assert AuditAction.EXPORT == 'export'
	assert AuditAction.FLUSH == 'flush'
	assert AuditAction.COMPACT == 'compact'
