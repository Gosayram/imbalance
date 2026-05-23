from __future__ import annotations

import hashlib
import uuid

import aiosqlite


class ToolResultReceipts:
	def __init__(self, db: aiosqlite.Connection) -> None:
		self.db = db

	async def store(
		self,
		*,
		session_id: str,
		tool_name: str,
		content: str,
		ref_path: str | None = None,
		preview_chars: int = 500,
	) -> str:
		receipt_id = f'tr_{uuid.uuid4().hex[:12]}'
		content_bytes = content.encode('utf-8')
		await self.db.execute(
			"""
			INSERT INTO tool_result_receipts(
				id, session_id, tool_name, content_hash, preview, bytes, ref_path
			)
			VALUES (?, ?, ?, ?, ?, ?, ?)
			""",
			(
				receipt_id,
				session_id,
				tool_name,
				hashlib.sha256(content_bytes).hexdigest(),
				content[:preview_chars],
				len(content_bytes),
				ref_path,
			),
		)
		await self.db.commit()
		return receipt_id
