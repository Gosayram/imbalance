import gc
import os
import tracemalloc
import pytest
import aiosqlite
from pathlib import Path
from unittest.mock import AsyncMock


@pytest.fixture
async def graph_db(tmp_path):
	db = await aiosqlite.connect(tmp_path / 'test_graph.db')
	db.row_factory = aiosqlite.Row
	await db.executescript("""
		CREATE TABLE IF NOT EXISTS code_symbols (
			id INTEGER PRIMARY KEY,
			kb_name TEXT NOT NULL,
			name TEXT NOT NULL,
			kind TEXT NOT NULL,
			file_path TEXT NOT NULL,
			line INTEGER NOT NULL,
			end_line INTEGER NOT NULL,
			signature TEXT NOT NULL,
			language TEXT NOT NULL
		);
		CREATE TABLE IF NOT EXISTS trigram_index (
			trigram TEXT NOT NULL,
			rowid INTEGER NOT NULL
		);
	""")
	await db.commit()
	yield db
	await db.close()


@pytest.fixture
def python_project(tmp_path) -> Path:
	src = tmp_path / 'src'
	src.mkdir()

	(src / 'auth.py').write_text("""
class TokenService:
	def rotate(self, token_id: int) -> bool:
		pass

	async def invalidate_all(self, user_id: int) -> None:
		pass

def refresh_token(session_id: str) -> str:
	svc = TokenService()
	return svc.rotate(session_id)
""")
	(src / 'models.py').write_text("""
from dataclasses import dataclass

@dataclass
class User:
	id: int
	email: str
""")
	(src / 'syntax_error.py').write_text('def broken(')

	(tmp_path / '.gitignore').write_text('__pycache__/\n*.pyc\n')
	(tmp_path / 'imbalance.toml').write_text('[project]\nname = "test"')
	return tmp_path


@pytest.fixture
def memory_tracker():
	class MemoryTracker:
		def __enter__(self):
			gc.collect()
			gc.collect()
			tracemalloc.start()
			self._snapshot_before = tracemalloc.take_snapshot()
			return self

		def __exit__(self, *args):
			gc.collect()
			gc.collect()
			snapshot_after = tracemalloc.take_snapshot()
			tracemalloc.stop()

			stats = snapshot_after.compare_to(self._snapshot_before, 'lineno')
			self.memory_delta_bytes = sum(s.size_diff for s in stats)
			self.top_leaks = [s for s in stats if s.size_diff > 1024][:5]

		def assert_no_leak(self, threshold_kb: int = 100):
			delta_kb = self.memory_delta_bytes / 1024
			if delta_kb > threshold_kb:
				leaks_str = '\n'.join(str(s) for s in self.top_leaks)
				pytest.fail(
					f'Memory leak detected: +{delta_kb:.1f} KB '
					f'(threshold: {threshold_kb} KB)\n'
					f'Top allocations:\n{leaks_str}'
				)

	return MemoryTracker()