import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from imbalance.core.embeddings import EmbeddingConfig, OpenAICompatProvider, OllamaProvider, build_provider


def test_embedding_config_defaults():
	config = EmbeddingConfig(provider="test", model="model")
	assert config.provider == "test"
	assert config.model == "model"


def test_ollama_provider_init():
	prov = OllamaProvider()
	assert prov.dimension == 768
	assert prov.model == "nomic-embed-text:v1.5"


def test_ollama_provider_with_params():
	prov = OllamaProvider(model="custom", base_url="http://localhost:1234")
	assert prov.dimension == 768


def test_openai_provider_init():
	prov = OpenAICompatProvider()
	assert prov.dimension == 1536


def test_openai_provider_with_params():
	prov = OpenAICompatProvider(model="custom", api_key="key", base_url="http://localhost")
	assert prov.dimension == 1536


@pytest.mark.asyncio
async def test_build_provider_none():
	result = await build_provider(None)
	assert result is None


@pytest.mark.asyncio
async def test_build_provider_none_provider():
	config = EmbeddingConfig(provider="none", model="test")
	result = await build_provider(config)
	assert result is None


@pytest.mark.asyncio
async def test_build_provider_unknown():
	config = EmbeddingConfig(provider="unknown", model="test")
	result = await build_provider(config)
	assert result is None


@pytest.mark.asyncio
async def test_ollama_ping_success():
	import sys
	from unittest.mock import AsyncMock
	mock_module = type(sys)('ollama')
	mock_client = AsyncMock()
	mock_client.ps = AsyncMock()
	mock_module.AsyncClient = lambda host=None: mock_client
	sys.modules['ollama'] = mock_module
	
	prov = OllamaProvider()
	result = await prov.ping()
	assert result is True
	del sys.modules['ollama']


@pytest.mark.asyncio
async def test_ollama_ping_failure():
	import sys
	from unittest.mock import AsyncMock
	mock_module = type(sys)('ollama')
	mock_client = AsyncMock()
	mock_client.ps = AsyncMock(side_effect=Exception("error"))
	mock_module.AsyncClient = lambda host=None: mock_client
	sys.modules['ollama'] = mock_module
	
	prov = OllamaProvider()
	result = await prov.ping()
	assert result is False
	del sys.modules['ollama']


def test_openai_provider_url():
	prov = OpenAICompatProvider(base_url="http:// custom")
	assert prov.base_url == "http:// custom"


@pytest.mark.asyncio
async def test_build_provider_ollama():
	config = EmbeddingConfig(provider="ollama", model="test")
	with patch("imbalance.core.embeddings.OllamaProvider") as mock_prov:
		result = await build_provider(config)
		mock_prov.assert_called()


@pytest.mark.asyncio
async def test_build_provider_openai():
	config = EmbeddingConfig(provider="openai", model="text-embedding-3-small", api_key="key")
	result = await build_provider(config)
	assert result is not None


@pytest.mark.asyncio
async def test_build_provider_openrouter():
	config = EmbeddingConfig(provider="openrouter", model="test", api_key="key")
	result = await build_provider(config)
	assert result is not None


@pytest.mark.asyncio
async def test_build_provider_ollama_not_available():
	import sys
	original = sys.modules.get('ollama')
	if 'ollama' in sys.modules:
		del sys.modules['ollama']
	# Make ollama import fail
	sys.modules['ollama'] = None
	try:
		config = EmbeddingConfig(provider="ollama", model="test")
		result = await build_provider(config)
		assert result is None
	finally:
		if original:
			sys.modules['ollama'] = original
		elif 'ollama' in sys.modules:
			del sys.modules['ollama']


def test_openai_provider_url():
	prov = OpenAICompatProvider(base_url="http:// custom")
	assert prov.base_url == "http:// custom"


def test_embedding_config_all_fields():
	config = EmbeddingConfig(provider="test", model="model", api_key="key", base_url="http://localhost")
	assert config.provider == "test"
	assert config.model == "model"
	assert config.api_key == "key"
	assert config.base_url == "http://localhost"
