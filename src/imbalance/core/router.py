from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI, OpenAIError

from imbalance.core.circuit_breaker import CircuitBreaker, CircuitOpenError

logger = logging.getLogger(__name__)

FREE_MODELS = [
	'qwen/qwen3-coder:free',
	'deepseek/deepseek-v4-flash:free',
	'meta-llama/llama-3.3-70b-instruct:free',
	'openrouter/free',
]

ALL_PROVIDERS_UNAVAILABLE = 'All providers unavailable'


class AllProvidersUnavailable(RuntimeError):
	pass


class ModelRouter:
	_breakers: dict[str, CircuitBreaker]

	def __init__(
		self,
		openrouter_key: str | None = None,
		ollama_base_url: str | None = None,
		ollama_model: str | None = None,
	) -> None:
		self.openrouter_key = openrouter_key
		self._breakers = {}
		self._ollama_base_url = ollama_base_url or 'http://localhost:11434'
		self._ollama_model = ollama_model or 'qwen3:8b'
		if openrouter_key:
			self._client = AsyncOpenAI(
				api_key=openrouter_key,
				base_url='https://openrouter.ai/api/v1',
			)

	def _get_breaker(self, model: str) -> CircuitBreaker:
		if model not in self._breakers:
			self._breakers[model] = CircuitBreaker(
				name=model,
				failure_threshold=3,
				recovery_timeout=60,
				success_threshold=2,
			)
		return self._breakers[model]

	async def complete(
		self,
		prompt: str,
		max_tokens: int = 600,
		model: str | None = None,
	) -> str:
		if self.openrouter_key and hasattr(self, '_client') and self._client is not None:
			models_to_try = [model] if model else FREE_MODELS

			for model_name in models_to_try:
				cb = self._get_breaker(model_name)
				try:
					return await cb.call(
						lambda m=model_name: self._call_openrouter(m, prompt, max_tokens),
					)
				except CircuitOpenError:
					continue
				except OpenAIError as e:
					logger.warning(f'{model_name} failed: {e}')
					continue

		try:
			return await self._call_ollama(prompt, max_tokens)
		except Exception as e:
			logger.warning(f'Ollama fallback failed: {e}')

		raise AllProvidersUnavailable(ALL_PROVIDERS_UNAVAILABLE)

	async def stream_complete(
		self,
		prompt: str,
		max_tokens: int = 600,
		model: str | None = None,
	) -> AsyncIterator[str]:
		if not self.openrouter_key:
			raise AllProvidersUnavailable('No OpenRouter API key configured')

		if not hasattr(self, '_client') or self._client is None:
			raise AllProvidersUnavailable('OpenRouter client not initialized')

		model_name = model or FREE_MODELS[0]
		stream = await self._client.chat.completions.create(
			model=model_name,
			messages=[{'role': 'user', 'content': prompt}],
			max_tokens=max_tokens,
			temperature=0.3,
			stream=True,
		)
		async for chunk in stream:
			delta = chunk.choices[0].delta.content if chunk.choices else None
			if delta:
				yield delta

	async def _call_openrouter(self, model: str, prompt: str, max_tokens: int) -> str:
		response = await self._client.chat.completions.create(
			model=model,
			messages=[{'role': 'user', 'content': prompt}],
			max_tokens=max_tokens,
			temperature=0.3,
		)
		if not response.choices:
			raise OpenAIError('No choices returned from model')
		content = response.choices[0].message.content
		if content is None:
			raise OpenAIError('Empty response from model')
		return content

	async def _call_ollama(self, prompt: str, max_tokens: int) -> str:
		client = AsyncOpenAI(
			api_key='ollama',
			base_url=self._ollama_base_url.rstrip('/') + '/v1',
		)
		response = await client.chat.completions.create(
			model=self._ollama_model,
			messages=[{'role': 'user', 'content': prompt}],
			max_tokens=max_tokens,
			temperature=0.3,
		)
		if not response.choices:
			raise RuntimeError('No choices from Ollama')
		content = response.choices[0].message.content
		if content is None:
			raise RuntimeError('Empty response from Ollama')
		return content

	async def apply_delta(self, delta_json: str, db_session_manager: Any) -> None:
		try:
			delta = json.loads(delta_json)
		except json.JSONDecodeError as err:
			raise ValueError('Invalid delta JSON') from err

		summary = delta.get('summary', '')
		decisions = delta.get('decisions', [])

		if not isinstance(summary, str):
			raise ValueError('Summary must be a string')
		if not isinstance(decisions, list):
			raise ValueError('Decisions must be a list')
		for d in decisions:
			if not isinstance(d, dict):
				raise ValueError('Each decision must be a dict')

		db = db_session_manager
		kb_name = delta.get('kb_name', 'default')

		await db.execute(
			"""
			INSERT INTO memory_summary(kb_name, content, token_count)
			VALUES (?, ?, ?)
			ON CONFLICT(kb_name) DO UPDATE SET
				content=excluded.content,
				token_count=excluded.token_count,
				updated_at=strftime('%Y-%m-%dT%H:%M:%SZ','now')
			""",
			(kb_name, summary, len(summary.split())),
		)
		await db.commit()

		logger.info(f'Delta applied: {len(summary)} chars summary, {len(decisions)} decisions')
