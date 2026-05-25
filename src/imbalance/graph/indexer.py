from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import Iterator
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import aiosqlite

from imbalance.graph._constants import SKIP_DIRS, SOURCE_EXTS
from imbalance.graph.models import IndexStats, Symbol
from imbalance.graph.parser import FileParser
from imbalance.graph.trigram import build_trigram_index

logger = logging.getLogger(__name__)


def _walk_files(project_dir: Path) -> Iterator[str]:
	stack = [project_dir]
	while stack:
		current = stack.pop()
		try:
			with os.scandir(current) as it:
				for entry in it:
					if entry.is_dir(follow_symlinks=False):
						if entry.name not in SKIP_DIRS:
							stack.append(Path(entry.path))
					elif entry.is_file(follow_symlinks=False):
						p = Path(entry.path)
						if p.suffix.lower() in SOURCE_EXTS:
							yield str(p)
		except PermissionError:
			continue


def _parse_batch(file_paths: list[str]) -> list[Symbol]:
	parser = FileParser()
	symbols: list[Symbol] = []
	for fp in file_paths:
		symbols.extend(parser.parse(fp))
	return symbols


class GraphIndexer:
	def __init__(self, project_path: Path, db: aiosqlite.Connection, kb_name: str):
		self.project_path = project_path
		self.db = db
		self.kb_name = kb_name
		self._parser = FileParser()

	async def index_full(self) -> IndexStats:
		start_time = time.perf_counter()

		files = list(_walk_files(self.project_path))
		n_workers = min(os.cpu_count() or 4, 8)
		batch_size = max(10, len(files) // n_workers) if files else 10

		all_symbols: list[Symbol] = []
		loop = asyncio.get_event_loop()

		with ProcessPoolExecutor(
			max_workers=n_workers,
			max_tasks_per_child=200,
		) as executor:
			batches = [files[i : i + batch_size] for i in range(0, len(files), batch_size)]

			for i in range(0, len(batches), 4):
				chunk = batches[i : i + 4]
				futures = [loop.run_in_executor(executor, _parse_batch, b) for b in chunk]
				results = await asyncio.gather(*futures, return_exceptions=True)

				for result in results:
					if isinstance(result, Exception):
						logger.warning(f'Batch parse error: {result}')
						continue
					all_symbols.extend(result)

				if len(all_symbols) >= 10_000:
					await self._insert_symbols(all_symbols)
					all_symbols.clear()

		if all_symbols:
			await self._insert_symbols(all_symbols)
			all_symbols.clear()

		await self._resolve_trigrams()

		elapsed_ms = (time.perf_counter() - start_time) * 1000

		return IndexStats(
			files=len(files),
			symbols=await self._count_symbols(),
			edges=0,
			duration_ms=elapsed_ms,
			peak_rss_mb=0.0,
		)

	async def _insert_symbols(self, symbols: list[Symbol]) -> None:
		await self.db.executemany(
			"""
			INSERT INTO code_symbols
				(kb_name, name, kind, file_path, line, end_line, signature, language)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?)
			""",
			[
				(
					self.kb_name,
					s.name,
					s.kind,
					s.file_path,
					s.line,
					s.end_line,
					s.signature,
					s.language,
				)
				for s in symbols
			],
		)
		await self.db.commit()

	async def _count_symbols(self) -> int:
		row = await self.db.execute_fetchone(
			'SELECT COUNT(*) FROM code_symbols WHERE kb_name = ?',
			(self.kb_name,),
		)
		return row[0] if row else 0

	async def _resolve_trigrams(self) -> None:
		rows = await self.db.execute_fetchall(
			'SELECT id, name FROM code_symbols WHERE kb_name = ?',
			(self.kb_name,),
		)
		symbol_ids = {r['name']: r['id'] for r in rows}
		if symbol_ids:
			await build_trigram_index(self.db, symbol_ids)
