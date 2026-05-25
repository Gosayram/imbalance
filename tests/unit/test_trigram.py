import pytest
from unittest.mock import AsyncMock
from imbalance.graph.trigram import _extract_trigrams, trigram_search, build_trigram_index
import aiosqlite


def test_extract_trigrams_short():
	assert _extract_trigrams("ab") == frozenset()


def test_extract_trigrams_basic():
	result = _extract_trigrams("hello")
	assert "hel" in result
	assert "ell" in result
	assert "llo" in result


def test_extract_trigrams_lowercase():
	result = _extract_trigrams("HELLO")
	assert "hel" in result


def test_extract_trigrams_empty():
	assert _extract_trigrams("") == frozenset()


@pytest.mark.asyncio
async def test_trigram_search_short_query():
	mock_db = AsyncMock()
	result = await trigram_search(mock_db, "a", "kb1")
	assert result == []


@pytest.mark.asyncio
async def test_build_trigram_index(tmp_path):
	db_path = tmp_path / "test.db"
	db = await aiosqlite.connect(db_path)
	await db.execute("CREATE TABLE trigram_index (trigram TEXT, rowid INTEGER)")
	await db.commit()
	symbol_ids = {"hello": 1, "world": 2}
	result = await build_trigram_index(db, symbol_ids)
	assert result > 0
