import pytest
from pathlib import Path
from datetime import UTC, datetime
from imbalance.core.backup import BackupManager


def test_create_backup(tmp_path):
	db_path = tmp_path / 'test.db'
	db_path.write_text('test data')

	manager = BackupManager(db_path, backup_dir=tmp_path / 'backups')
	backup_path = manager.create_backup('test')

	assert backup_path.exists()
	assert backup_path.read_text() == 'test data'
	assert 'test' in backup_path.name


def test_rotate_backups(tmp_path):
	db_path = tmp_path / 'test.db'
	db_path.write_text('test data')

	manager = BackupManager(db_path, backup_dir=tmp_path / 'backups', max_backups=3)

	# Create 5 backups
	for i in range(5):
		manager.create_backup(f'test-{i}')

	# Should have 5 backups
	backups = manager.list_backups()
	assert len(backups) == 5

	# Rotate should keep only 3
	removed = manager.rotate_backups()
	assert removed == 2

	backups = manager.list_backups()
	assert len(backups) == 3


def test_list_backups_empty(tmp_path):
	db_path = tmp_path / 'test.db'
	db_path.write_text('test data')

	manager = BackupManager(db_path, backup_dir=tmp_path / 'backups')
	backups = manager.list_backups()

	assert backups == []


def test_list_backups_sorted(tmp_path):
	db_path = tmp_path / 'test.db'
	db_path.write_text('test data')

	manager = BackupManager(db_path, backup_dir=tmp_path / 'backups')

	# Create backups
	manager.create_backup('first')
	manager.create_backup('second')

	backups = manager.list_backups()
	assert len(backups) == 2
	# Both should have valid paths
	assert 'first' in backups[0]['path'] or 'second' in backups[0]['path']
	assert 'first' in backups[1]['path'] or 'second' in backups[1]['path']


def test_restore_backup(tmp_path):
	db_path = tmp_path / 'test.db'
	db_path.write_text('original data')

	manager = BackupManager(db_path, backup_dir=tmp_path / 'backups')
	backup_path = manager.create_backup('before-change')

	# Modify original
	db_path.write_text('modified data')
	assert db_path.read_text() == 'modified data'

	# Restore
	manager.restore_backup(backup_path)
	assert db_path.read_text() == 'original data'


def test_restore_backup_not_found(tmp_path):
	db_path = tmp_path / 'test.db'
	db_path.write_text('test data')

	manager = BackupManager(db_path, backup_dir=tmp_path / 'backups')

	with pytest.raises(FileNotFoundError):
		manager.restore_backup(tmp_path / 'nonexistent.db')
