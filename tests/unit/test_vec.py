import pytest
from unittest.mock import AsyncMock
from imbalance.storage.vec import search_by_embedding


@pytest.mark.asyncio
async def test_search_by_embedding_unavailable():
	db = AsyncMock()
	results = await search_by_embedding(db, [0.1, 0.2, 0.3], limit=5)
	assert results == []
