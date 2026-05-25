import pytest
from unittest.mock import AsyncMock
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
