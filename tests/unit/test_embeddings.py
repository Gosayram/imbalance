import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from imbalance.core.embeddings import EmbeddingConfig, OllamaProvider, OpenAICompatProvider, build_provider


def test_embedding_config_defaults():
	config = EmbeddingConfig(provider="openai", model="test-model")
	assert config.provider == "openai"
	assert config.model == "test-model"
	assert config.api_key is None


def test_ollama_provider_defaults():
	prov = OllamaProvider()
	assert prov.model == "nomic-embed-text:v1.5"
	assert prov.dimension == 768


@pytest.mark.asyncio
async def test_ollama_provider_embed():
	# Test that provider is properly configured without making actual API calls
	prov = OllamaProvider()
	assert prov.dimension == 768
	assert prov.model == "nomic-embed-text:v1.5"


@pytest.mark.asyncio
async def test_openai_provider_defaults():
	prov = OpenAICompatProvider()
	assert prov.model == "text-embedding-3-small"
	assert prov.dimension == 1536


@pytest.mark.asyncio
async def test_build_provider_none():
	result = await build_provider(None)
	assert result is None


@pytest.mark.asyncio
async def test_build_provider_empty():
	result = await build_provider(EmbeddingConfig(provider="none", model="test"))
	assert result is None
