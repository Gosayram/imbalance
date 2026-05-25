import pytest
from imbalance.core.dedup import _jaccard_similarity, DedupResult, _cosine_similarity, JACCARD_THRESHOLD


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
