import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from imbalance.storage.vec import search_by_embedding, _floats_to_blob


@pytest.mark.asyncio
async def test_search_by_embedding_unavailable():
	db = AsyncMock()
	results = await search_by_embedding(db, [0.1, 0.2, 0.3], limit=5)
	assert results == []


@pytest.mark.asyncio
async def test_search_by_embedding_with_results():
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[
		{'section_id': 1, 'distance': 0.5},
		{'section_id': 2, 'distance': 0.7},
	])
	results = await search_by_embedding(db, [0.1, 0.2, 0.3])
	assert len(results) == 2
	assert results[0]['section_id'] == 1


def test_floats_to_blob():
	result = _floats_to_blob([1.0, 2.0, 3.0])
	assert isinstance(result, bytes)
	assert len(result) == 12  # 3 floats * 4 bytes each


@pytest.mark.asyncio
async def test_is_vec_available_import_error():
	db = AsyncMock()
	with patch.dict("sys.modules", {"sqlite_vec": None}):
		import sys
		sys.modules["sqlite_vec"] = None
		from imbalance.storage.vec import is_vec_available
		result = await is_vec_available(db)
		assert result is False


@pytest.mark.asyncio
async def test_ensure_vec_table_unavailable():
	db = AsyncMock()
	with patch("imbalance.storage.vec.is_vec_available", return_value=False):
		from imbalance.storage.vec import ensure_vec_table
		result = await ensure_vec_table(db)
		assert result is False


@pytest.mark.asyncio
async def test_upsert_embedding():
	db = AsyncMock()
	from imbalance.storage.vec import upsert_embedding
	await upsert_embedding(db, 1, [1.0, 2.0, 3.0])
	db.execute.assert_called()


@pytest.mark.asyncio
async def test_delete_embedding():
	db = AsyncMock()
	from imbalance.storage.vec import delete_embedding
	await delete_embedding(db, 1)
	db.execute.assert_called()
