import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from imbalance.core.backup import BackupManager


def test_backup_manager_init():
	db_path = Path('/tmp/test.db')
	manager = BackupManager(db_path)
	assert manager.db_path == db_path
	assert manager.max_backups == 7
	assert manager.max_age_days == 30


def test_backup_manager_custom_config():
	db_path = Path('/tmp/test.db')
	manager = BackupManager(db_path, max_backups=5, max_age_days=7)
	assert manager.max_backups == 5
	assert manager.max_age_days == 7


def test_backup_manager_custom_backup_dir():
	db_path = Path('/tmp/test.db')
	backup_dir = Path('/tmp/backups')
	manager = BackupManager(db_path, backup_dir=backup_dir)
	assert manager.backup_dir == backup_dir


def test_create_backup_with_reason(tmp_path):
	db_path = tmp_path / 'test.db'
	db_path.write_text('test data')

	manager = BackupManager(db_path, backup_dir=tmp_path / 'backups')
	backup_path = manager.create_backup('pre-compact')

	assert backup_path.exists()
	assert 'pre-compact' in backup_path.name


def test_rotate_backups_removes_oldest(tmp_path):
	db_path = tmp_path / 'test.db'
	db_path.write_text('test data')

	manager = BackupManager(db_path, backup_dir=tmp_path / 'backups', max_backups=2)

	# Create 3 backups
	manager.create_backup('first')
	manager.create_backup('second')
	manager.create_backup('third')

	# Should have 3 backups
	backups = manager.list_backups()
	assert len(backups) == 3

	# Rotate should keep only 2
	removed = manager.rotate_backups()
	assert removed == 1

	backups = manager.list_backups()
	assert len(backups) == 2


def test_list_backups_returns_dict(tmp_path):
	db_path = tmp_path / 'test.db'
	db_path.write_text('test data')

	manager = BackupManager(db_path, backup_dir=tmp_path / 'backups')
	manager.create_backup('test')

	backups = manager.list_backups()
	assert len(backups) == 1
	assert 'path' in backups[0]
	assert 'size_bytes' in backups[0]
	assert 'created_at' in backups[0]


def test_restore_backup_creates_pre_restore(tmp_path):
	db_path = tmp_path / 'test.db'
	db_path.write_text('original')

	manager = BackupManager(db_path, backup_dir=tmp_path / 'backups')
	backup_path = manager.create_backup('before')

	db_path.write_text('modified')
	manager.restore_backup(backup_path)

	# Should have created a pre-restore backup
	backups = manager.list_backups()
	assert any('pre-restore' in b['path'] for b in backups)


def test_restore_backup_restores_content(tmp_path):
	db_path = tmp_path / 'test.db'
	db_path.write_text('original')

	manager = BackupManager(db_path, backup_dir=tmp_path / 'backups')
	backup_path = manager.create_backup('before')

	db_path.write_text('modified')
	assert db_path.read_text() == 'modified'

	manager.restore_backup(backup_path)
	assert db_path.read_text() == 'original'
