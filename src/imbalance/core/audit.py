from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)


class AuditAction(StrEnum):
	"""Audit log actions."""
	CREATE = 'create'
	UPDATE = 'update'
	DELETE = 'delete'
	ARCHIVE = 'archive'
	RESTORE = 'restore'
	IMPORT = 'import'
	EXPORT = 'export'
	FLUSH = 'flush'
	COMPACT = 'compact'


class AuditLogger:
	"""Audit logger for KB changes."""

	def __init__(self, db: aiosqlite.Connection, kb_name: str) -> None:
		self.db = db
		self.kb_name = kb_name

	async def log(
		self,
		action: AuditAction,
		resource_type: str,
		resource_id: str,
		details: dict[str, Any] | None = None,
		user_id: str | None = None,
		session_id: str | None = None,
	) -> None:
		"""Log an audit event.

		Args:
			action: Action performed
			resource_type: Type of resource (wiki_section, session, etc.)
			resource_id: ID of resource
			details: Additional details
			user_id: User who performed action
			session_id: Session ID
		"""
		await self.db.execute(
			"""INSERT INTO audit_log
			(kb_name, action, resource_type, resource_id, details, user_id, session_id, timestamp)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
			(
				self.kb_name,
				action.value,
				resource_type,
				resource_id,
				json.dumps(details) if details else None,
				user_id,
				session_id,
				datetime.now(UTC).isoformat(),
			),
		)
		await self.db.commit()

		logger.info(
			f'Audit: {action.value} {resource_type}/{resource_id}',
			extra={'audit': True, 'action': action.value, 'resource': resource_id},
		)

	async def get_logs(
		self,
		resource_type: str | None = None,
		resource_id: str | None = None,
		action: AuditAction | None = None,
		limit: int = 100,
	) -> list[dict[str, Any]]:
		"""Get audit logs.

		Args:
			resource_type: Filter by resource type
			resource_id: Filter by resource ID
			action: Filter by action
			limit: Maximum number of results

		Returns:
			List of audit log entries
		"""
		query = 'SELECT * FROM audit_log WHERE kb_name=?'
		params: list[Any] = [self.kb_name]

		if resource_type:
			query += ' AND resource_type=?'
			params.append(resource_type)
		if resource_id:
			query += ' AND resource_id=?'
			params.append(resource_id)
		if action:
			query += ' AND action=?'
			params.append(action.value)

		query += ' ORDER BY timestamp DESC LIMIT ?'
		params.append(limit)

		rows = await self.db.execute_fetchall(query, params)
		return [dict(row) for row in rows]


async def ensure_audit_table(db: aiosqlite.Connection) -> None:
	"""Ensure audit_log table exists."""
	await db.execute("""
		CREATE TABLE IF NOT EXISTS audit_log (
			id INTEGER PRIMARY KEY,
			kb_name TEXT NOT NULL,
			action TEXT NOT NULL,
			resource_type TEXT NOT NULL,
			resource_id TEXT NOT NULL,
			details TEXT,
			user_id TEXT,
			session_id TEXT,
			timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
		)
	""")
	await db.execute(
		'CREATE INDEX IF NOT EXISTS idx_audit_log_kb ON audit_log(kb_name, timestamp)'
	)
	await db.commit()
