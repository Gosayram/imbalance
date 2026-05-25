import pytest
from unittest.mock import AsyncMock, MagicMock
from imbalance.core.consolidation import consolidate_raw_memories, ConsolidationResult


@pytest.mark.asyncio
async def test_consolidate_no_raw_memories():
	mock_store = MagicMock()
	mock_store.fetch_unconsumed_raw_memories = AsyncMock(return_value=[])
	mock_router = MagicMock()
	result = await consolidate_raw_memories(mock_store, mock_router)
	assert result.updated is False


@pytest.mark.asyncio
async def test_consolidate_with_raw_memories():
	mock_store = MagicMock()
	mock_store.fetch_unconsumed_raw_memories = AsyncMock(return_value=[
		{'id': 1, 'memory_type': 'observation', 'confidence': 0.9, 'session_id': 'session-123', 'content': 'test content'}
	])
	mock_store.get_memory_summary = AsyncMock(return_value='')
	mock_store.upsert_memory_summary = AsyncMock()
	mock_store.mark_raw_memories_consumed = AsyncMock()
	
	mock_router = MagicMock()
	mock_router.complete = AsyncMock(return_value='Updated summary')
	
	result = await consolidate_raw_memories(mock_store, mock_router, max_summary_tokens=100, batch_limit=10)
	assert result.updated is True
	assert result.memories_consumed == 1
