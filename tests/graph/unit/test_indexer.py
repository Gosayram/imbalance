import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from imbalance.graph.indexer import _walk_files, _parse_batch, GraphIndexer
from imbalance.graph.models import Symbol


def test_walk_files_empty(tmp_path):
	result = list(_walk_files(tmp_path))
	assert result == []


def test_walk_files_with_file(tmp_path):
	test_file = tmp_path / "test.py"
	test_file.write_text("pass")
	result = list(_walk_files(tmp_path))
	assert len(result) == 1


def test_walk_files_skips_dirs(tmp_path):
	venv = tmp_path / "venv"
	venv.mkdir()
	(venv / "test.py").write_text("pass")
	result = list(_walk_files(tmp_path))
	assert len(result) == 0


def test_parse_batch_returns_symbols():
	symbols = _parse_batch([])
	assert isinstance(symbols, list)


def test_parse_batch_with_file(tmp_path):
	test_file = tmp_path / "test.py"
	test_file.write_text("def hello():\n    pass\n")
	symbols = _parse_batch([str(test_file)])
	assert len(symbols) > 0


def test_walk_files_skip_git(tmp_path):
	git = tmp_path / ".git"
	git.mkdir()
	(git / "test.py").write_text("pass")
	result = list(_walk_files(tmp_path))
	assert len(result) == 0


def test_walk_files_skip_node_modules(tmp_path):
	nm = tmp_path / "node_modules"
	nm.mkdir()
	(nm / "test.js").write_text("pass")
	result = list(_walk_files(tmp_path))
	assert len(result) == 0


def test_walk_files_multiple_files(tmp_path):
	(tmp_path / "a.py").write_text("pass")
	(tmp_path / "b.py").write_text("pass")
	result = list(_walk_files(tmp_path))
	assert len(result) == 2


def test_walk_files_skip_hidden(tmp_path):
	hidden = tmp_path / ".git"
	hidden.mkdir()
	(hidden / "test.py").write_text("pass")
	result = list(_walk_files(tmp_path))
	assert len(result) == 0


@pytest.mark.asyncio
async def test_graph_indexer_init():
	db = AsyncMock()
	indexer = GraphIndexer(Path("."), db, "test_kb")
	assert indexer.kb_name == "test_kb"


@pytest.mark.asyncio
async def test_insert_symbols():
	db = AsyncMock()
	indexer = GraphIndexer(Path("."), db, "test_kb")
	await indexer._insert_symbols([])
	db.executemany.assert_called()


@pytest.mark.asyncio
async def test_count_symbols():
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[{'cnt': 5}])
	indexer = GraphIndexer(Path("."), db, "test_kb")
	count = await indexer._count_symbols()
	assert count == 5


@pytest.mark.asyncio
async def test_count_symbols_empty():
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[])
	indexer = GraphIndexer(Path("."), db, "test_kb")
	count = await indexer._count_symbols()
	assert count == 0


@pytest.mark.asyncio
async def test_resolve_trigrams():
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[{'id': 1, 'name': 'test'}])
	indexer = GraphIndexer(Path("."), db, "test_kb")
	await indexer._resolve_trigrams()
	db.execute_fetchall.assert_called()


@pytest.mark.asyncio
async def test_index_project_no_db():
	indexer = GraphIndexer(Path("."), None, "test_kb")
	with pytest.raises(Exception):
		await indexer.index_project()


def test_walk_files_permission_error(tmp_path):
	# Mock scandir to raise PermissionError
	with patch("imbalance.graph.indexer.os.scandir") as mock_scandir:
		mock_scandir.side_effect = PermissionError("access denied")
		result = list(_walk_files(tmp_path))
		assert result == []


@pytest.mark.asyncio
async def test_index_full_empty(tmp_path):
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[])
	indexer = GraphIndexer(tmp_path, db, "test_kb")
	stats = await indexer.index_full()
	assert stats.files == 0


def test_walk_files_deep_nested(tmp_path):
	# Test line 30 - stack.append for non-skipped directories
	(tmp_path / "subdir").mkdir()
	(tmp_path / "subdir" / "a.py").write_text("pass")
	result = list(_walk_files(tmp_path))
	assert len(result) == 1


@pytest.mark.asyncio
async def test_index_full_with_files(tmp_path):
	# Test the ProcessPoolExecutor path in index_full - covers lines 85-87
	(tmp_path / "test.py").write_text("def hello():\n    pass\n")
	mock_db = AsyncMock()
	mock_db.execute_fetchall = AsyncMock(return_value=[])
	
	# Mock ProcessPoolExecutor to avoid actual multiprocessing
	with patch("imbalance.graph.indexer.ProcessPoolExecutor") as mock_ppe:
		mock_executor = MagicMock()
		mock_ppe.return_value.__enter__ = MagicMock(return_value=mock_executor)
		mock_ppe.return_value.__exit__ = MagicMock(return_value=False)
		
		loop = asyncio.get_event_loop()
		original_run_in_executor = loop.run_in_executor
		
		# Mock to call _parse_batch and return real Symbol objects
		def mock_run_in_executor(executor, func, arg):
			fut = asyncio.Future()
			fut.set_result(func(arg))
			return fut
		
		loop.run_in_executor = mock_run_in_executor
		
		try:
			indexer = GraphIndexer(tmp_path, mock_db, "test_kb")
			stats = await indexer.index_full()
			assert stats.files >= 1
			# Verify _insert_symbols was called (line 86)
			assert mock_db.executemany.call_count >= 1
		finally:
			loop.run_in_executor = original_run_in_executor


@pytest.mark.asyncio
async def test_index_full_batch_error(tmp_path):
	# Test exception handling in batch processing - covers lines 76-78
	(tmp_path / "test.py").write_text("pass")
	mock_db = AsyncMock()
	mock_db.execute_fetchall = AsyncMock(return_value=[])
	
	with patch("imbalance.graph.indexer.ProcessPoolExecutor") as mock_ppe:
		mock_executor = MagicMock()
		mock_ppe.return_value.__enter__ = MagicMock(return_value=mock_executor)
		mock_ppe.return_value.__exit__ = MagicMock(return_value=False)
		
		loop = asyncio.get_event_loop()
		original_run_in_executor = loop.run_in_executor
		
		def mock_run_in_executor(executor, func, arg):
			fut = asyncio.Future()
			fut.set_result(Exception("batch error"))
			return fut
		
		loop.run_in_executor = mock_run_in_executor
		
		try:
			indexer = GraphIndexer(tmp_path, mock_db, "test_kb")
			stats = await indexer.index_full()
			assert stats.files >= 1
		finally:
			loop.run_in_executor = original_run_in_executor


@pytest.mark.asyncio
async def test_index_full_threshold_insert(tmp_path):
	# Test threshold path - covers lines 81-83
	(tmp_path / "test.py").write_text("def hello(): pass")
	mock_db = AsyncMock()
	mock_db.execute_fetchall = AsyncMock(return_value=[])
	
	with patch("imbalance.graph.indexer.ProcessPoolExecutor") as mock_ppe:
		mock_executor = MagicMock()
		mock_ppe.return_value.__enter__ = MagicMock(return_value=mock_executor)
		mock_ppe.return_value.__exit__ = MagicMock(return_value=False)
		
		loop = asyncio.get_event_loop()
		original_run_in_executor = loop.run_in_executor
		
		# Return enough Symbol objects to trigger threshold (>= 10_000)
		many_symbols = [Symbol(name=f"func_{i}", kind="function", file_path="test.py", line=i, end_line=i+1, signature="", language="python") for i in range(10_001)]
		
		def mock_run_in_executor(executor, func, arg):
			fut = asyncio.Future()
			fut.set_result(many_symbols)
			return fut
		
		loop.run_in_executor = mock_run_in_executor
		
		try:
			indexer = GraphIndexer(tmp_path, mock_db, "test_kb")
			stats = await indexer.index_full()
			assert stats.files >= 1
			# Verify insert was called (threshold triggered)
			assert mock_db.executemany.call_count >= 1
		finally:
			loop.run_in_executor = original_run_in_executor