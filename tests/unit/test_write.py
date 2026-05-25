import pytest
from unittest.mock import AsyncMock, MagicMock
from imbalance.core.write import WriteEngine, SaveResult, _default_slug, machine_id


def test_default_slug_special_section():
	assert _default_slug("stack") == "stack"
	assert _default_slug("context") == "context"


def test_default_slug_regular_section():
	result = _default_slug("decisions")
	assert result.startswith("decisions/")


def test_machine_id():
	result = machine_id()
	assert ":" in result


@pytest.mark.asyncio
async def test_save_fact_basic():
	mock_store = MagicMock()
	mock_store.kb_name = "test_kb"
	mock_store.upsert_section = AsyncMock(return_value=1)
	mock_store.db = MagicMock()
	
	engine = WriteEngine(mock_store)
	result = await engine.save_fact(content="test content", section="decisions")
	assert result.slug is not None
	assert result.token_count > 0
