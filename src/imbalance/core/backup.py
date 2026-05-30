from __future__ import annotations

import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class BackupManager:
	"""Manages database backups with rotation."""

	def __init__(
		self,
		db_path: Path,
		backup_dir: Path | None = None,
		max_backups: int = 7,
		max_age_days: int = 30,
	) -> None:
		self.db_path = db_path
		self.backup_dir = backup_dir or db_path.parent / 'backups'
		self.max_backups = max_backups
		self.max_age_days = max_age_days

	def create_backup(self, reason: str = 'manual') -> Path:
		"""Create a new backup.

		Args:
			reason: Reason for backup (manual, pre-compact, pre-import)

		Returns:
			Path to the created backup
		"""
		self.backup_dir.mkdir(parents=True, exist_ok=True)

		timestamp = datetime.now(UTC).strftime('%Y%m%d_%H%M%S')
		backup_name = f'{self.db_path.stem}_{timestamp}_{reason}.db'
		backup_path = self.backup_dir / backup_name

		shutil.copy2(self.db_path, backup_path)
		logger.info(f'Created backup: {backup_path}')

		return backup_path

	def rotate_backups(self) -> int:
		"""Rotate old backups, keeping max_backups most recent.

		Returns:
			Number of backups removed
		"""
		if not self.backup_dir.exists():
			return 0

		backups = sorted(
			self.backup_dir.glob('*.db'),
			key=lambda p: p.stat().st_mtime,
			reverse=True,
		)

		removed = 0

		# Remove backups exceeding max_backups
		for backup in backups[self.max_backups:]:
			backup.unlink()
			logger.info(f'Removed old backup: {backup}')
			removed += 1

		# Remove backups older than max_age_days
		cutoff = datetime.now(UTC).timestamp() - (self.max_age_days * 86400)
		for backup in backups[: self.max_backups]:
			if backup.stat().st_mtime < cutoff:
				backup.unlink()
				logger.info(f'Removed expired backup: {backup}')
				removed += 1

		return removed

	def list_backups(self) -> list[dict]:
		"""List all backups.

		Returns:
			List of backup info dicts
		"""
		if not self.backup_dir.exists():
			return []

		backups = []
		for backup in sorted(
			self.backup_dir.glob('*.db'),
			key=lambda p: p.stat().st_mtime,
			reverse=True,
		):
			stat = backup.stat()
			backups.append({
				'path': str(backup),
				'size_bytes': stat.st_size,
				'created_at': datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
			})

		return backups

	def restore_backup(self, backup_path: Path) -> None:
		"""Restore database from backup.

		Args:
			backup_path: Path to backup file

		Raises:
			FileNotFoundError: If backup doesn't exist
		"""
		if not backup_path.exists():
			raise FileNotFoundError(f'Backup not found: {backup_path}')

		# Create a backup of current state before restore
		self.create_backup('pre-restore')

		shutil.copy2(backup_path, self.db_path)
		logger.info(f'Restored from backup: {backup_path}')
