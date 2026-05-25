import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from imbalance.core.write import WriteEngine, SaveResult, machine_id, _default_slug


def test_machine_id():
	result = machine_id()
	assert ':' in result


def test_default_slug_standard():
	assert _default_slug('stack') == 'stack'
	assert _default_slug('context') == 'context'


def test_default_slug_uuid():
	slug = _default_slug('custom')
	assert slug.startswith('custom/')


@pytest.mark.asyncio
async def test_write_engine_save_fact():
	mock_store = MagicMock()
	mock_store.upsert_section = AsyncMock(return_value=1)
	mock_store.db = AsyncMock()
	
	engine = WriteEngine(mock_store)
	result = await engine.save_fact(content="test content", section="context")
	assert result.slug == "context"
	assert result.section_id == 1


@pytest.mark.asyncio
async def test_write_engine_save_fact_custom_slug():
	mock_store = MagicMock()
	mock_store.upsert_section = AsyncMock(return_value=1)
	mock_store.db = AsyncMock()
	
	engine = WriteEngine(mock_store)
	result = await engine.save_fact(content="test content", section="context", slug="custom-slug")
	assert result.slug == "custom-slug"


@pytest.mark.asyncio
async def test_write_engine_save_fact_with_router():
	mock_store = MagicMock()
	mock_store.upsert_section = AsyncMock(return_value=1)
	mock_store.db = AsyncMock()
	mock_router = MagicMock()
	mock_router.complete = AsyncMock(return_value="tag1, tag2")
	
	engine = WriteEngine(mock_store, router=mock_router)
	result = await engine.save_fact(content="test content", section="custom")
	assert result.slug.startswith("custom/")
