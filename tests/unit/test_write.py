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


def test_default_slug_issues():
	assert _default_slug('issues') == 'issues'


def test_default_slug_about():
	assert _default_slug('about') == 'about'


def test_save_result():
	result = SaveResult(slug="test", section_id=1, token_count=100)
	assert result.slug == "test"
	assert result.section_id == 1
	assert result.token_count == 100


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


@pytest.mark.asyncio
async def test_write_engine_save_fact_no_dedup():
	mock_store = MagicMock()
	mock_store.upsert_section = AsyncMock(return_value=1)
	mock_store.db = AsyncMock()
	
	engine = WriteEngine(mock_store)
	result = await engine.save_fact(content="test content", section="custom", dedup=False)
	assert result.slug.startswith("custom/")


@pytest.mark.asyncio
async def test_write_engine_save_fact_with_tags():
	mock_store = MagicMock()
	mock_store.upsert_section = AsyncMock(return_value=1)
	mock_store.db = AsyncMock()
	
	engine = WriteEngine(mock_store)
	result = await engine.save_fact(content="test content", section="context", tags=["tag1", "tag2"])
	assert result.slug == "context"
