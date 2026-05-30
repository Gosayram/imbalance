import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from imbalance.core.router import (
	ModelRouter,
	AllProvidersUnavailable,
	FREE_MODELS,
)


def test_router_init_all_params():
	router = ModelRouter(
		openrouter_key='or-key',
		anthropic_key='ant-key',
		ollama_base_url='http://custom:11434',
		ollama_model='custom-model',
	)
	assert router.openrouter_key == 'or-key'
	assert router.anthropic_key == 'ant-key'
	assert router._ollama_base_url == 'http://custom:11434'
	assert router._ollama_model == 'custom-model'


def test_free_models_contains_expected():
	assert 'qwen/qwen3-coder:free' in FREE_MODELS
	assert 'deepseek/deepseek-v4-flash:free' in FREE_MODELS
	assert 'meta-llama/llama-3.3-70b-instruct:free' in FREE_MODELS
	assert 'openrouter/free' in FREE_MODELS


def test_free_models_all_strings():
	for model in FREE_MODELS:
		assert isinstance(model, str)


@pytest.mark.asyncio
async def test_router_complete_no_providers():
	router = ModelRouter()
	with pytest.raises(AllProvidersUnavailable):
		await router.complete('test')


@pytest.mark.asyncio
async def test_router_stream_complete_no_providers():
	router = ModelRouter()
	with pytest.raises(AllProvidersUnavailable):
		async for _ in router.stream_complete('test'):
			pass


def test_all_providers_unavailable_message():
	error = AllProvidersUnavailable('custom message')
	assert str(error) == 'custom message'
	assert error.args[0] == 'custom message'


def test_router_has_circuit_breakers():
	router = ModelRouter()
	assert hasattr(router, '_breakers')
