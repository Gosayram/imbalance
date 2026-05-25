import pytest
from unittest.mock import AsyncMock, MagicMock
from imbalance.storage.store import SQLiteStore, _truncate_words


@pytest.mark.asyncio
async def test_truncate_words_short():
	result = _truncate_words("hello world", 10)
	assert result == "hello world"


@pytest.mark.asyncio
async def test_truncate_words_long():
	text = "one two three four five six seven eight nine ten eleven"
	result = _truncate_words(text, 5)
	assert result == "one two three four five"


@pytest.mark.asyncio
async def test_store_upsert_section():
	db = AsyncMock()
	db.execute = AsyncMock(return_value=AsyncMock(lastrowid=1))
	db._fetchone = AsyncMock(return_value={'id': 1})
	store = SQLiteStore(db, "test")
	section_id = await store.upsert_section(
		slug="test-slug", section="overview", content="content", token_count=10
	)
	assert section_id == 1


@pytest.mark.asyncio
async def test_store_fts_search():
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[])
	store = SQLiteStore(db, "test")
	results = await store.fts_search("query")
	assert results == []


@pytest.mark.asyncio
async def test_store_get_memory_summary_none():
	db = AsyncMock()
	cursor = AsyncMock()
	cursor.fetchone = AsyncMock(return_value=None)
	db.execute = AsyncMock(return_value=cursor)
	store = SQLiteStore(db, "test")
	result = await store.get_memory_summary(100)
	assert result is None


@pytest.mark.asyncio
async def test_store_mark_raw_memories_consumed_empty():
	db = AsyncMock()
	store = SQLiteStore(db, "test")
	await store.mark_raw_memories_consumed([])
	# Should return early without calling execute
