import pytest
from unittest.mock import AsyncMock, MagicMock
from imbalance.core.query import (
	QueryEngine,
	rrf_merge,
	score_chunks,
	_cache_key,
	DEFAULT_SCOPE_WEIGHTS,
	RRF_K,
)
from imbalance.core.context import ContextChunk, ContextMode


def test_cache_key_empty_query():
	key = _cache_key('', 2000, None)
	assert len(key) == 16


def test_cache_key_with_multiple_scopes():
	key1 = _cache_key('test', 2000, ('decisions', 'context'))
	key2 = _cache_key('test', 2000, ('context', 'decisions'))
	assert key1 == key2  # Sorted scopes should produce same key


def test_cache_key_different_budgets():
	key1 = _cache_key('test', 1000, None)
	key2 = _cache_key('test', 2000, None)
	assert key1 != key2


def test_rrf_merge_with_custom_weights():
	fts = ContextChunk(slug='a', section='decisions', content='a', score=1.0, token_count=10, confidence=1.0)
	vec = ContextChunk(slug='b', section='context', content='b', score=1.0, token_count=10, confidence=1.0)

	# Decisions should rank higher with default weights
	result = rrf_merge([fts], [vec])
	assert result[0].slug == 'a'

	# Context should rank higher with custom weights
	result = rrf_merge([fts], [vec], scope_weights={'context': 2.0, 'decisions': 0.5})
	assert result[0].slug == 'b'


def test_rrf_merge_confidence_impact():
	high_conf = ContextChunk(slug='a', section='decisions', content='a', score=1.0, token_count=10, confidence=1.0)
	low_conf = ContextChunk(slug='b', section='decisions', content='b', score=1.0, token_count=10, confidence=0.0)

	result = rrf_merge([high_conf], [low_conf], confidence_weight=0.1)
	assert result[0].slug == 'a'


def test_score_chunks_custom_weights():
	chunks = [
		ContextChunk(slug='a', section='decisions', content='a', score=1.0, token_count=10, confidence=1.0),
		ContextChunk(slug='b', section='context', content='b', score=1.0, token_count=10, confidence=1.0),
	]

	# Decisions should rank higher with default weights
	result = score_chunks(chunks, 'test')
	assert result[0].slug == 'a'

	# Context should rank higher with custom weights
	result = score_chunks(chunks, 'test', scope_weights={'context': 2.0, 'decisions': 0.5})
	assert result[0].slug == 'b'


def test_score_chunks_confidence_impact():
	chunks = [
		ContextChunk(slug='a', section='decisions', content='a', score=1.0, token_count=10, confidence=1.0),
		ContextChunk(slug='b', section='decisions', content='b', score=1.0, token_count=10, confidence=0.0),
	]

	result = score_chunks(chunks, 'test', confidence_weight=0.1)
	assert result[0].slug == 'a'


def test_default_scope_weights():
	assert 'decisions' in DEFAULT_SCOPE_WEIGHTS
	assert 'context' in DEFAULT_SCOPE_WEIGHTS
	assert 'stack' in DEFAULT_SCOPE_WEIGHTS
	assert 'issues' in DEFAULT_SCOPE_WEIGHTS
	assert 'about' in DEFAULT_SCOPE_WEIGHTS


def test_rrf_k_value():
	assert RRF_K == 60


def test_query_engine_init():
	store = MagicMock()
	engine = QueryEngine(store)
	assert engine.store is store
	assert engine.memory_mode == ContextMode.READ_WRITE


def test_query_engine_init_with_custom_params():
	store = MagicMock()
	engine = QueryEngine(
		store,
		memory_mode=ContextMode.READ_ONLY,
		cache_ttl=900,
		cache_maxsize=128,
		confidence_weight=0.1,
	)
	assert engine.memory_mode == ContextMode.READ_ONLY
	assert engine._confidence_weight == 0.1
