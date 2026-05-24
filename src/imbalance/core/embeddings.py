from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
	dimension: int

	async def embed(self, texts: list[str]) -> list[list[float]]: ...


@dataclass(frozen=True)
class EmbeddingConfig:
	provider: str
	model: str
	api_key: str | None = None
	base_url: str | None = None


class OllamaProvider:
	def __init__(self, model: str = 'nomic-embed-text:v1.5', base_url: str | None = None) -> None:
		self.model = model
		self.base_url = base_url
		self.dimension = 768

	async def embed(self, texts: list[str]) -> list[list[float]]:
		import ollama

		client = ollama.AsyncClient(host=self.base_url)
		results = []
		for text in texts:
			resp = await client.embeddings(model=self.model, prompt=text)
			results.append(resp['embedding'])
		return results

	async def ping(self) -> bool:
		import ollama

		client = ollama.AsyncClient(host=self.base_url)
		try:
			await client.ps()
			return True
		except Exception:
			return False


class OpenAICompatProvider:
	def __init__(
		self,
		model: str = 'text-embedding-3-small',
		api_key: str | None = None,
		base_url: str | None = None,
	) -> None:
		self.model = model
		self.api_key = api_key
		self.base_url = base_url
		self.dimension = 1536

	async def embed(self, texts: list[str]) -> list[list[float]]:
		from openai import AsyncOpenAI

		client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
		resp = await client.embeddings.create(input=texts, model=self.model)
		return [item.embedding for item in resp.data]


async def build_provider(config: EmbeddingConfig | None) -> EmbeddingProvider | None:
	if config is None or config.provider in ('none', ''):
		return None

	if config.provider == 'ollama':
		try:
			prov = OllamaProvider(model=config.model, base_url=config.base_url)
			if await prov.ping():
				logger.info('Ollama embedding provider ready (model=%s)', config.model)
				return prov
			logger.warning('Ollama unavailable — falling back to FTS5-only mode')
			return None
		except ImportError:
			logger.warning('ollama package not installed — FTS5-only mode')
			return None
		except Exception as exc:
			logger.warning('Ollama init failed: %s — FTS5-only mode', exc)
			return None

	if config.provider in ('openai', 'openrouter'):
		try:
			base_url = config.base_url
			if config.provider == 'openrouter' and not base_url:
				base_url = 'https://openrouter.ai/api/v1'
			prov = OpenAICompatProvider(
				model=config.model,
				api_key=config.api_key,
				base_url=base_url,
			)
			logger.info('OpenAI-compat embedding provider ready (model=%s)', config.model)
			return prov
		except Exception as exc:
			logger.warning('OpenAI-compat init failed: %s — FTS5-only mode', exc)
			return None

	logger.warning('Unknown embedding provider: %s — FTS5-only mode', config.provider)
	return None
