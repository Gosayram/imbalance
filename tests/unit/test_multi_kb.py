import pytest
from unittest.mock import AsyncMock, MagicMock
from imbalance.core.multi_kb import MultiKBQuery
from imbalance.core.context import ContextPack, ContextChunk


@pytest.fixture
async def mock_primary():
	mock = MagicMock()
	mock.get_context_pack = AsyncMock(return_value=ContextPack(
		query="test",
		budget_tokens=100,
		precedence=["primary"],
		summary="primary summary",
		evidence=[ContextChunk(slug="a", section="test", content="content", score=0.9, token_count=10, confidence=0.9)],
		omitted=[],
		warnings=[]
	))
	return mock


@pytest.fixture
async def mock_inherited():
	mock = MagicMock()
	mock.get_context_pack = AsyncMock(return_value=ContextPack(
		query="test",
		budget_tokens=50,
		precedence=["inherited"],
		summary="inherited summary",
		evidence=[ContextChunk(slug="b", section="test", content="content", score=0.8, token_count=10, confidence=0.8)],
		omitted=[],
		warnings=[]
	))
	return mock


@pytest.mark.asyncio
async def test_multi_kb_without_inherited(mock_primary):
	multi = MultiKBQuery(primary=mock_primary, inherited=None)
	result = await multi.get_context_pack("test", budget_tokens=100)
	assert result.query == "test"


@pytest.mark.asyncio
async def test_multi_kb_with_inherited(mock_primary, mock_inherited):
	multi = MultiKBQuery(primary=mock_primary, inherited=mock_inherited, inherit_weight=0.5)
	result = await multi.get_context_pack("test", budget_tokens=100)
	assert len(result.evidence) == 2
