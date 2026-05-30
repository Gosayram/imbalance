import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from imbalance.core.router import ModelRouter, AllProvidersUnavailable, FREE_MODELS


def test_router_init_openrouter():
	router = ModelRouter(openrouter_key='test-key')
	assert router.openrouter_key == 'test-key'


def test_router_init_anthropic():
	router = ModelRouter(anthropic_key='test-key')
	assert router.anthropic_key == 'test-key'


def test_router_init_ollama():
	router = ModelRouter(ollama_base_url='http://localhost:11434', ollama_model='qwen3:8b')
	assert router._ollama_base_url == 'http://localhost:11434'
	assert router._ollama_model == 'qwen3:8b'


def test_router_init_defaults():
	router = ModelRouter()
	assert router._ollama_base_url == 'http://localhost:11434'
	assert router._ollama_model == 'qwen3:8b'


def test_free_models_list():
	assert len(FREE_MODELS) > 0
	assert all(isinstance(m, str) for m in FREE_MODELS)


@pytest.mark.asyncio
async def test_router_complete_no_keys():
	router = ModelRouter()
	with pytest.raises(AllProvidersUnavailable):
		await router.complete('test prompt')


@pytest.mark.asyncio
async def test_router_stream_complete_no_keys():
	router = ModelRouter()
	with pytest.raises(AllProvidersUnavailable):
		async for _ in router.stream_complete('test prompt'):
			pass


def test_all_providers_unavailable():
	error = AllProvidersUnavailable('test message')
	assert str(error) == 'test message'
