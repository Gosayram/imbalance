import pytest
from unittest.mock import AsyncMock, MagicMock
from imbalance.core.multi_kb import MultiKBQuery


@pytest.mark.asyncio
async def test_multi_kb_query_no_inherited():
	mock_primary = MagicMock()
	mock_pack = MagicMock()
	mock_pack.evidence = []
	mock_pack.summary = None
	mock_pack.warnings = []
	mock_pack.precedence = []
	mock_pack.omitted = []
	mock_primary.get_context_pack = AsyncMock(return_value=mock_pack)
	
	query = MultiKBQuery(primary=mock_primary)
	result = await query.get_context_pack("test", budget_tokens=100)
	assert result is not None


@pytest.mark.asyncio
async def test_multi_kb_query_with_inherited():
	mock_primary = MagicMock()
	mock_inherited = MagicMock()
	
	mock_pack = MagicMock()
	mock_pack.evidence = []
	mock_pack.summary = None
	mock_pack.warnings = []
	mock_pack.precedence = []
	mock_pack.omitted = []
	
	mock_primary.get_context_pack = AsyncMock(return_value=mock_pack)
	mock_inherited.get_context_pack = AsyncMock(return_value=mock_pack)
	
	query = MultiKBQuery(primary=mock_primary, inherited=mock_inherited, inherit_weight=0.5)
	result = await query.get_context_pack("test", budget_tokens=100)
	assert result is not None
