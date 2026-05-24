from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import aiosqlite

from imbalance.core.router import ModelRouter

logger = logging.getLogger(__name__)

MERGE_PROMPT = """You are a knowledge base curator for project {kb_name}.

## Existing content of section '{slug}':
{existing_content}

## New information from current session:
{new_content}

## Task:
Produce an updated version of this section. Rules:
1. MERGE: if new info updates or extends existing — produce unified text
2. SUPERSEDE: if new info contradicts existing — keep new, move old to
   a comment block: <!-- superseded: <old text> -->
3. ARCHIVE: if existing content is clearly obsolete (old sprint, closed
   issue, replaced decision) — mark with <!-- archived: <reason> -->
4. KEEP: if new info is unrelated to existing — append as new paragraph

Return ONLY the updated markdown content. No explanations. No fences.
Token budget for result: {budget} tokens maximum.
"""


@dataclass
class CompactionReport:
	archived: list[str] = field(default_factory=list)
	updated: list[str] = field(default_factory=list)
	evergreen: list[str] = field(default_factory=list)
	current: list[str] = field(default_factory=list)


async def smart_merge_section(
	router: ModelRouter,
	kb_name: str,
	slug: str,
	existing: str,
	new_content: str,
	budget_tokens: int = 400,
) -> str:
	if not existing.strip():
		return new_content

	existing_for_merge = existing[:2000] if len(existing) > 2000 else existing

	prompt = MERGE_PROMPT.format(
		kb_name=kb_name,
		slug=slug,
		existing_content=existing_for_merge,
		new_content=new_content,
		budget=budget_tokens,
	)
	merged = await router.complete(prompt, max_tokens=budget_tokens)
	return merged


class KBCompactor:
	def __init__(
		self,
		db: aiosqlite.Connection,
		router: ModelRouter,
		kb_name: str,
	) -> None:
		self.db = db
		self.router = router
		self.kb_name = kb_name

	async def run_full_compaction(self, dry_run: bool = False) -> CompactionReport:
		start = time.monotonic()
		report = CompactionReport()

		rows = await self.db.execute_fetchall(
			'SELECT id, slug, content, section, updated_at '
			'FROM wiki_sections WHERE kb_name=? AND archived=FALSE',
			(self.kb_name,),
		)

		for row in rows:
			slug = row['slug']
			content = row['content']

			if len(content) < 50:
				report.current.append(slug)
				continue

			if dry_run:
				report.current.append(slug)
				continue

			try:
				merged = await smart_merge_section(
					self.router,
					self.kb_name,
					slug,
					content,
					'Audit: check for staleness or contradictions.',
					budget_tokens=300,
				)
				token_count = max(1, len(merged.split()))
				await self.db.execute(
					"""UPDATE wiki_sections
					SET content=?, token_count=?,
						updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now')
					WHERE id=?""",
					(merged, token_count, row['id']),
				)
				report.updated.append(slug)
			except Exception as exc:
				logger.warning('Compaction failed for %s: %s', slug, exc)
				report.current.append(slug)

		await self.db.commit()

		duration = time.monotonic() - start
		await self.db.execute(
			"""INSERT INTO kb_compaction_log
			(kb_name, sections_total, sections_archived, sections_updated,
			 sections_evergreen, duration_sec)
			VALUES (?, ?, ?, ?, ?, ?)""",
			(
				self.kb_name,
				len(rows),
				len(report.archived),
				len(report.updated),
				len(report.evergreen),
				duration,
			),
		)
		await self.db.commit()

		return report
