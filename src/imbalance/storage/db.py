from __future__ import annotations

from importlib import resources
from pathlib import Path

import aiosqlite

MIGRATIONS_PACKAGE = 'imbalance.storage.migrations'


async def open_db(path: Path) -> aiosqlite.Connection:
	path.parent.mkdir(parents=True, exist_ok=True)
	db = await aiosqlite.connect(path)
	db.row_factory = aiosqlite.Row
	await db.executescript(
		"""
		PRAGMA journal_mode = WAL;
		PRAGMA synchronous = NORMAL;
		PRAGMA foreign_keys = ON;
		PRAGMA cache_size = -32000;
		PRAGMA mmap_size = 134217728;
		PRAGMA busy_timeout = 5000;
		PRAGMA wal_autocheckpoint = 100;
		"""
	)
	return db


async def run_migrations(db: aiosqlite.Connection) -> None:
	await db.execute(
		"""
		CREATE TABLE IF NOT EXISTS schema_migrations (
			version TEXT PRIMARY KEY,
			applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
		)
		"""
	)
	await db.commit()

	applied = {
		row['version'] for row in await db.execute_fetchall('SELECT version FROM schema_migrations')
	}

	migration_files = sorted(
		resources.files(MIGRATIONS_PACKAGE).iterdir(), key=lambda item: item.name
	)
	for migration in migration_files:
		if not migration.name.endswith('.sql'):
			continue
		version = migration.name.split('_', 1)[0]
		if version in applied:
			continue
		await db.executescript(migration.read_text(encoding='utf-8'))
		await db.execute('INSERT INTO schema_migrations(version) VALUES (?)', (version,))
		await db.commit()


async def checkpoint(db: aiosqlite.Connection, mode: str = 'PASSIVE') -> None:
	allowed = {'PASSIVE', 'FULL', 'RESTART', 'TRUNCATE'}
	if mode not in allowed:
		raise ValueError(f'Unsupported checkpoint mode: {mode}')
	await db.execute(f'PRAGMA wal_checkpoint({mode})')
	await db.commit()


async def integrity_check(db: aiosqlite.Connection) -> str:
	cursor = await db.execute('PRAGMA integrity_check')
	row = await cursor.fetchone()
	if row is None:
		raise RuntimeError('SQLite returned no integrity_check result')
	return str(row[0])
