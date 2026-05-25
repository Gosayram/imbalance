from __future__ import annotations

import socket
import uuid
from dataclasses import dataclass
from getpass import getuser
from typing import Any

from imbalance.core.tokens import estimate_tokens
from imbalance.storage.store import SQLiteStore


@dataclass(frozen=True)
class SaveResult:
	slug: str
	section_id: int
	token_count: int


class WriteEngine:
	def __init__(self, store: SQLiteStore, router: Any = None) -> None:
		self.store = store
		self._router = router

	async def save_fact(
		self,
		*,
		content: str,
		section: str,
		slug: str | None = None,
		tags: list[str] | None = None,
		session_id: str | None = None,
		dedup: bool = True,
	) -> SaveResult:
		final_slug = slug or _default_slug(section)

		if dedup and not slug:
			from imbalance.core.dedup import dedup_check

			result = await dedup_check(self.store.db, self.store.kb_name, content, section)
			if result.is_duplicate and result.existing_slug:
				final_slug = result.existing_slug

		final_tags = tags
		if final_tags is None and self._router:
			try:
				prompt = f'Extract 3-5 relevant tags from this content (comma-separated, no quotes): "{content[:500]}"'
				resp = await self._router.complete(prompt, max_tokens=50)
				final_tags = [t.strip() for t in resp.split(',')][:5]
			except Exception:
				final_tags = []
		elif final_tags is None:
			final_tags = []

		token_count = estimate_tokens(content)
		section_id = await self.store.upsert_section(
			slug=final_slug,
			section=section,
			content=content,
			token_count=token_count,
			session_id=session_id,
			machine_id=machine_id(),
			tags=final_tags or [],
		)
		return SaveResult(slug=final_slug, section_id=section_id, token_count=token_count)


def machine_id() -> str:
	return f'{socket.gethostname()}:{getuser()}'


def _default_slug(section: str) -> str:
	if section in {'stack', 'context', 'issues', 'about'}:
		return section
	return f'{section}/{uuid.uuid4().hex[:8]}'
