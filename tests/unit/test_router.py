import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from imbalance.core.router import ModelRouter, AllProvidersUnavailable, FREE_MODELS


def test_router_init_no_key():
	router = ModelRouter()
	assert router.openrouter_key is None


def test_router_init_with_key():
	router = ModelRouter(openrouter_key="test-key")
	assert router.openrouter_key == "test-key"


def test_free_models():
	assert len(FREE_MODELS) > 0
	assert 'qwen/qwen3-coder:free' in FREE_MODELS


def test_all_providers_unavailable():
	err = AllProvidersUnavailable("test")
	assert str(err) == "test"


@pytest.mark.asyncio
async def test_router_complete_no_key():
	router = ModelRouter()
	with pytest.raises(AllProvidersUnavailable):
		await router.complete("test prompt")


@pytest.mark.asyncio
async def test_router_stream_complete_no_key():
	router = ModelRouter()
	with pytest.raises(AllProvidersUnavailable):
		async for _ in router.stream_complete("test"):
			pass


@pytest.mark.asyncio
async def test_router_complete_with_key():
	with patch("imbalance.core.router.AsyncOpenAI") as mock_client_class:
		mock_client = AsyncMock()
		mock_response = MagicMock()
		mock_response.choices = [MagicMock(message=MagicMock(content="response"))]
		mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
		mock_client_class.return_value = mock_client
		
		router = ModelRouter(openrouter_key="test-key")
		result = await router.complete("test")
		assert result == "response"


@pytest.mark.asyncio
async def test_router_apply_delta_invalid_json():
	router = ModelRouter()
	with pytest.raises(ValueError):
		await router.apply_delta("not json", AsyncMock())


@pytest.mark.asyncio
async def test_router_apply_delta_invalid_summary():
	router = ModelRouter()
	db = AsyncMock()
	with pytest.raises(ValueError):
		await router.apply_delta('{"summary": 123}', db)


@pytest.mark.asyncio
async def test_router_apply_delta_invalid_decisions():
	router = ModelRouter()
	db = AsyncMock()
	with pytest.raises(ValueError):
		await router.apply_delta('{"summary": "test", "decisions": "not a list"}', db)


@pytest.mark.asyncio
async def test_router_apply_delta_invalid_decision_type():
	router = ModelRouter()
	db = AsyncMock()
	with pytest.raises(ValueError):
		await router.apply_delta('{"summary": "test", "decisions": ["not a dict"]}', db)
