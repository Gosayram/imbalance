from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetryConfig:
	"""Retry configuration."""
	max_retries: int = 3
	base_delay: float = 1.0
	max_delay: float = 30.0
	exponential_base: float = 2.0
	retryable_exceptions: tuple[type[Exception], ...] = (Exception,)


class RetryError(Exception):
	"""Retry exhausted error."""

	def __init__(self, last_exception: Exception, attempts: int) -> None:
		self.last_exception = last_exception
		self.attempts = attempts
		super().__init__(f'Retry exhausted after {attempts} attempts: {last_exception}')


async def retry_async(
	func: Callable[..., Any],
	*args: Any,
	config: RetryConfig | None = None,
	**kwargs: Any,
) -> Any:
	"""Retry async function with exponential backoff.

	Args:
		func: Async function to retry
		*args: Function arguments
		config: Retry configuration
		**kwargs: Function keyword arguments

	Returns:
		Function result

	Raises:
		RetryError: If all retries exhausted
	"""
	cfg = config or RetryConfig()
	last_exception: Exception | None = None

	for attempt in range(cfg.max_retries + 1):
		try:
			return await func(*args, **kwargs)
		except cfg.retryable_exceptions as e:
			last_exception = e
			if attempt < cfg.max_retries:
				delay = min(
					cfg.base_delay * (cfg.exponential_base ** attempt),
					cfg.max_delay,
				)
				logger.warning(
					f'Retry {attempt + 1}/{cfg.max_retries} after {delay:.1f}s: {e}'
				)
				await asyncio.sleep(delay)

	raise RetryError(last_exception, cfg.max_retries + 1)


def retry_sync(
	func: Callable[..., Any],
	*args: Any,
	config: RetryConfig | None = None,
	**kwargs: Any,
) -> Any:
	"""Retry synchronous function with exponential backoff.

	Args:
		func: Function to retry
		*args: Function arguments
		config: Retry configuration
		**kwargs: Function keyword arguments

	Returns:
		Function result

	Raises:
		RetryError: If all retries exhausted
	"""
	import time

	cfg = config or RetryConfig()
	last_exception: Exception | None = None

	for attempt in range(cfg.max_retries + 1):
		try:
			return func(*args, **kwargs)
		except cfg.retryable_exceptions as e:
			last_exception = e
			if attempt < cfg.max_retries:
				delay = min(
					cfg.base_delay * (cfg.exponential_base ** attempt),
					cfg.max_delay,
				)
				logger.warning(
					f'Retry {attempt + 1}/{cfg.max_retries} after {delay:.1f}s: {e}'
				)
				time.sleep(delay)

	raise RetryError(last_exception, cfg.max_retries + 1)
