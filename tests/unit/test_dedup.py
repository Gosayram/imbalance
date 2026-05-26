import pytest
from unittest.mock import AsyncMock
from imbalance.core.dedup import _jaccard_similarity, DedupResult, _cosine_similarity, JACCARD_THRESHOLD, dedup_check


def test_jaccard_similarity_identical():
	assert _jaccard_similarity("hello world", "hello world") == 1.0


def test_jaccard_similarity_no_overlap():
	assert _jaccard_similarity("hello world", "foo bar") == 0.0


def test_jaccard_similarity_partial():
	sim = _jaccard_similarity("hello world", "hello foo")
	assert 0 < sim < 1


def test_jaccard_similarity_empty():
	assert _jaccard_similarity("", "test") == 0.0


def test_cosine_similarity_identical():
	assert abs(_cosine_similarity([1.0, 1.0], [1.0, 1.0]) - 1.0) < 0.0001


def test_cosine_similarity_orthogonal():
	assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_cosine_similarity_zero_vector():
	assert _cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_dedup_result():
	result = DedupResult(is_duplicate=True, existing_slug="test", similarity=0.8)
	assert result.is_duplicate is True
	assert result.existing_slug == "test"
	assert result.similarity == 0.8


@pytest.mark.asyncio
async def test_dedup_check_no_rows():
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[])
	result = await dedup_check(db, "test_kb", "content", "decisions")
	assert result.is_duplicate is False


@pytest.mark.asyncio
async def test_dedup_check_jaccard_duplicate():
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[{'slug': 'existing', 'content': 'hello world'}])
	result = await dedup_check(db, "test_kb", "hello world", "decisions")
	assert result.is_duplicate is True
	assert result.existing_slug == 'existing'


@pytest.mark.asyncio
async def test_dedup_check_jaccard_no_duplicate():
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[{'slug': 'existing', 'content': 'completely different content here'}])
	result = await dedup_check(db, "test_kb", "hello world", "decisions")
	assert result.is_duplicate is False
