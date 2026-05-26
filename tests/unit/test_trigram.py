import pytest
from unittest.mock import AsyncMock, MagicMock
from imbalance.graph.trigram import _extract_trigrams, trigram_search, build_trigram_index


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


def test_extract_trigrams_single_char():
	assert _extract_trigrams("a") == frozenset()


def test_extract_trigrams_two_chars():
	assert _extract_trigrams("ab") == frozenset()


@pytest.mark.asyncio
async def test_trigram_search_short_query():
	mock_db = AsyncMock()
	result = await trigram_search(mock_db, "a", "kb1")
	assert result == []


@pytest.mark.asyncio
async def test_trigram_search_query_too_short():
	mock_db = AsyncMock()
	result = await trigram_search(mock_db, "x", "kb1")
	assert result == []


@pytest.mark.asyncio
async def test_trigram_search_no_trigrams():
	mock_db = AsyncMock()
	result = await trigram_search(mock_db, "", "kb1")
	assert result == []


@pytest.mark.asyncio
async def test_trigram_search_with_results():
	mock_db = AsyncMock()
	mock_db.execute_fetchall = AsyncMock(return_value=[
		{'id': 1, 'name': 'func', 'kind': 'function', 'file_path': 'test.py', 'line': 10}
	])
	result = await trigram_search(mock_db, "fun", "kb1")
	assert len(result) == 1
	assert result[0]['name'] == 'func'


@pytest.mark.asyncio
async def test_trigram_search_limit():
	mock_db = AsyncMock()
	mock_db.execute_fetchall = AsyncMock(return_value=[])
	result = await trigram_search(mock_db, "test", "kb1", limit=5)
	assert result == []


@pytest.mark.asyncio
async def test_trigram_search_query_two_chars():
	# Query "ab" returns no trigrams (len < 3), but passes the len < 2 check
	mock_db = AsyncMock()
	result = await trigram_search(mock_db, "ab", "kb1")
	assert result == []


@pytest.mark.asyncio
async def test_build_trigram_index_empty():
	mock_db = AsyncMock()
	result = await build_trigram_index(mock_db, {})
	assert result == 0


@pytest.mark.asyncio
async def test_build_trigram_index_single():
	mock_db = AsyncMock()
	mock_db.executemany = AsyncMock()
	mock_db.commit = AsyncMock()
	result = await build_trigram_index(mock_db, {'function': 1})
	assert result == 6


@pytest.mark.asyncio
async def test_build_trigram_index_multiple():
	mock_db = AsyncMock()
	mock_db.executemany = AsyncMock()
	mock_db.commit = AsyncMock()
	result = await build_trigram_index(mock_db, {'hello': 1, 'world': 2})
	assert result > 0


def test_extract_trigrams_unicode():
	result = _extract_trigrams("héllo")
	assert len(result) > 0


def test_extract_trigrams_whitespace():
	result = _extract_trigrams("hello world")
	assert "hel" in result
	assert "wor" in result


@pytest.mark.asyncio
async def test_build_trigram_index_large_batch():
	mock_db = AsyncMock()
	mock_db.executemany = AsyncMock()
	mock_db.commit = AsyncMock()
	# Create a large batch to trigger the batch insertion logic
	symbol_ids = {f"symbol{i}": i for i in range(10000)}
	result = await build_trigram_index(mock_db, symbol_ids)
	assert result > 0
