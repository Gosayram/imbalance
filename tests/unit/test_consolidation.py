import pytest
from unittest.mock import AsyncMock
from imbalance.core.consolidation import ConsolidationResult, consolidate_raw_memories, CONSOLIDATE_MEMORY_PROMPT


def test_consolidation_result_no_update():
	result = ConsolidationResult(updated=False)
	assert result.updated is False
	assert result.summary is None


def test_consolidation_result_updated():
	result = ConsolidationResult(updated=True, summary="test", memories_consumed=5)
	assert result.updated is True
	assert result.summary == "test"
	assert result.memories_consumed == 5


@pytest.mark.asyncio
async def test_consolidate_no_raw_memories():
	store = AsyncMock()
	store.fetch_unconsumed_raw_memories = AsyncMock(return_value=[])
	router = AsyncMock()
	result = await consolidate_raw_memories(store, router)
	assert result.updated is False


@pytest.mark.asyncio
async def test_consolidate_with_raw_memories():
	store = AsyncMock()
	store.fetch_unconsumed_raw_memories = AsyncMock(return_value=[
		{'id': 1, 'memory_type': 'test', 'confidence': 0.5, 'session_id': 'sess123', 'content': 'test content'}
	])
	store.get_memory_summary = AsyncMock(return_value='')
	store.upsert_memory_summary = AsyncMock()
	store.mark_raw_memories_consumed = AsyncMock()
	router = AsyncMock()
	router.complete = AsyncMock(return_value='new summary')
	result = await consolidate_raw_memories(store, router)
	assert result.updated is True
	assert result.memories_consumed == 1


@pytest.mark.asyncio
async def test_consolidate_router_error():
	store = AsyncMock()
	store.fetch_unconsumed_raw_memories = AsyncMock(return_value=[
		{'id': 1, 'memory_type': 'test', 'confidence': 0.5, 'session_id': 'sess123', 'content': 'test content'}
	])
	store.get_memory_summary = AsyncMock(return_value='')
	router = AsyncMock()
	router.complete = AsyncMock(side_effect=Exception("error"))
	result = await consolidate_raw_memories(store, router)
	assert result.updated is False


@pytest.mark.asyncio
async def test_consolidate_with_existing_summary():
	store = AsyncMock()
	store.fetch_unconsumed_raw_memories = AsyncMock(return_value=[
		{'id': 1, 'memory_type': 'test', 'confidence': 0.5, 'session_id': 'sess123', 'content': 'test content'}
	])
	store.get_memory_summary = AsyncMock(return_value='existing summary')
	store.upsert_memory_summary = AsyncMock()
	store.mark_raw_memories_consumed = AsyncMock()
	router = AsyncMock()
	router.complete = AsyncMock(return_value='new summary')
	result = await consolidate_raw_memories(store, router)
	assert result.updated is True
	assert result.memories_consumed == 1
