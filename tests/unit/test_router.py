import pytest

from imbalance.core.router import AllProvidersUnavailable, ModelRouter


@pytest.mark.asyncio
async def test_router_rejects_without_api_key() -> None:
	router = ModelRouter(openrouter_key=None)
	with pytest.raises(AllProvidersUnavailable, match='No OpenRouter API key'):
		await router.complete('test prompt')


@pytest.mark.asyncio
async def test_router_raises_when_client_not_initialized() -> None:
	router = ModelRouter(openrouter_key='test-key')
	# Client is created in __init__ when key is provided, so this tests the actual flow
	# We just test that without proper key structure it fails early
	with pytest.raises(AllProvidersUnavailable):
		await router.complete('test prompt')