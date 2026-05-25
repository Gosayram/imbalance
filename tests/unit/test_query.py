import pytest
from unittest.mock import AsyncMock, MagicMock
from imbalance.core.query import QueryEngine, rrf_merge, PRECEDENCE, COMPACTED_PRECEDENCE
from imbalance.core.context import ContextChunk


def test_precedence():
	assert 'wiki_sections' in PRECEDENCE


def test_compacted_precedence():
	assert 'compaction_checkpoint' in COMPACTED_PRECEDENCE


def test_rrf_merge():
	fts = [ContextChunk(slug="a", section="test", content="c", score=0.5, token_count=10)]
	vec = [ContextChunk(slug="b", section="test", content="c", score=0.5, token_count=10)]
	result = rrf_merge(fts, vec)
	assert len(result) == 2


def test_rrf_merge_duplicate():
	fts = [ContextChunk(slug="a", section="test", content="c", score=0.5, token_count=10)]
	vec = [ContextChunk(slug="a", section="test", content="c", score=0.7, token_count=10)]
	result = rrf_merge(fts, vec)
	assert len(result) == 1  # Should deduplicate


@pytest.mark.asyncio
async def test_query_engine_init():
	mock_store = MagicMock()
	engine = QueryEngine(mock_store)
	assert engine.memory_mode.value == "read_write"


@pytest.mark.asyncio
async def test_query_engine_get_context_pack():
	mock_store = MagicMock()
	mock_store.get_memory_summary = AsyncMock(return_value=None)
	mock_store.fts_search = AsyncMock(return_value=[])
	mock_store.db = AsyncMock()
	mock_store.db.execute = AsyncMock()
	mock_store.db.commit = AsyncMock()
	
	engine = QueryEngine(mock_store)
	result = await engine.get_context_pack("test", budget_tokens=100)
	assert result.query == "test"


@pytest.mark.asyncio
async def test_query_engine_read_only_mode():
	mock_store = MagicMock()
	mock_store.get_memory_summary = AsyncMock(return_value=None)
	mock_store.fts_search = AsyncMock(return_value=[])
	mock_store.db = AsyncMock()
	mock_store.db.execute = AsyncMock()
	mock_store.db.commit = AsyncMock()
	
	from imbalance.core.context import ContextMode
	engine = QueryEngine(mock_store, memory_mode=ContextMode.READ_ONLY)
	result = await engine.get_context_pack("test", budget_tokens=100)
	assert any('read-only' in w for w in result.warnings)
