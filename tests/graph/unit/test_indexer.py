import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from imbalance.graph.indexer import _walk_files, _parse_batch, GraphIndexer


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
