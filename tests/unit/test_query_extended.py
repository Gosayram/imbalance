import pytest
from unittest.mock import AsyncMock, MagicMock
from imbalance.core.query import rrf_merge, score_chunks, _cache_key
from imbalance.core.context import ContextChunk


def test_cache_key_basic():
	key = _cache_key('test query', 2000, None)
	assert len(key) == 16
	assert isinstance(key, str)


def test_cache_key_with_scope():
	key1 = _cache_key('test', 2000, ('decisions',))
	key2 = _cache_key('test', 2000, ('context',))
	assert key1 != key2


def test_cache_key_same_inputs():
	key1 = _cache_key('test', 2000, ('decisions',))
	key2 = _cache_key('test', 2000, ('decisions',))
	assert key1 == key2


def test_rrf_merge_empty():
	result = rrf_merge([], [])
	assert result == []


def test_rrf_merge_fts_only():
	chunk = ContextChunk(
		slug='test',
		section='decisions',
		content='test content',
		score=1.0,
		token_count=100,
		confidence=1.0,
	)
	result = rrf_merge([chunk], [])
	assert len(result) == 1
	assert result[0].slug == 'test'


def test_rrf_merge_vec_only():
	chunk = ContextChunk(
		slug='test',
		section='decisions',
		content='test content',
		score=1.0,
		token_count=100,
		confidence=1.0,
	)
	result = rrf_merge([], [chunk])
	assert len(result) == 1
	assert result[0].slug == 'test'


def test_rrf_merge_both():
	fts_chunk = ContextChunk(
		slug='fts',
		section='decisions',
		content='fts content',
		score=1.0,
		token_count=100,
		confidence=1.0,
	)
	vec_chunk = ContextChunk(
		slug='vec',
		section='decisions',
		content='vec content',
		score=1.0,
		token_count=100,
		confidence=1.0,
	)
	result = rrf_merge([fts_chunk], [vec_chunk])
	assert len(result) == 2


def test_rrf_merge_same_slug():
	fts_chunk = ContextChunk(
		slug='same',
		section='decisions',
		content='fts content',
		score=1.0,
		token_count=100,
		confidence=1.0,
	)
	vec_chunk = ContextChunk(
		slug='same',
		section='decisions',
		content='vec content',
		score=1.0,
		token_count=100,
		confidence=1.0,
	)
	result = rrf_merge([fts_chunk], [vec_chunk])
	assert len(result) == 1
	assert result[0].slug == 'same'


def test_score_chunks_empty():
	result = score_chunks([], 'test query')
	assert result == []


def test_score_chunks_single():
	chunk = ContextChunk(
		slug='test',
		section='decisions',
		content='test content',
		score=1.0,
		token_count=100,
		confidence=1.0,
	)
	result = score_chunks([chunk], 'test query')
	assert len(result) == 1
	assert result[0].slug == 'test'


def test_score_chunks_ordering():
	high_score = ContextChunk(
		slug='high',
		section='decisions',
		content='high score',
		score=2.0,
		token_count=100,
		confidence=1.0,
	)
	low_score = ContextChunk(
		slug='low',
		section='decisions',
		content='low score',
		score=0.5,
		token_count=100,
		confidence=1.0,
	)
	result = score_chunks([low_score, high_score], 'test query')
	assert result[0].slug == 'high'
	assert result[1].slug == 'low'


def test_score_chunks_confidence_boost():
	high_conf = ContextChunk(
		slug='high',
		section='decisions',
		content='high confidence',
		score=1.0,
		token_count=100,
		confidence=1.0,
	)
	low_conf = ContextChunk(
		slug='low',
		section='decisions',
		content='low confidence',
		score=1.0,
		token_count=100,
		confidence=0.1,
	)
	result = score_chunks([low_conf, high_conf], 'test query', confidence_weight=0.1)
	assert result[0].slug == 'high'
	assert result[1].slug == 'low'
