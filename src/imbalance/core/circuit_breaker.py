from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import TypeVar

T = TypeVar('T')


class CircuitState(StrEnum):
	CLOSED = 'closed'
	OPEN = 'open'
	HALF_OPEN = 'half_open'


class CircuitOpenError(RuntimeError):
	"""Raised while a provider circuit is cooling down."""


class CircuitBreaker:
	def __init__(
		self,
		name: str,
		*,
		failure_threshold: int = 3,
		recovery_timeout: float = 60.0,
		success_threshold: int = 2,
		clock: Callable[[], float] = time.monotonic,
	) -> None:
		if min(failure_threshold, success_threshold) < 1:
			raise ValueError('Thresholds must be positive')
		if recovery_timeout < 0:
			raise ValueError('recovery_timeout must be non-negative')
		self.name = name
		self.failure_threshold = failure_threshold
		self.recovery_timeout = recovery_timeout
		self.success_threshold = success_threshold
		self._clock = clock
		self.state = CircuitState.CLOSED
		self.failures = 0
		self.successes = 0
		self.opened_at: float | None = None

	async def call(self, operation: Callable[[], Awaitable[T]]) -> T:
		self._before_call()
		try:
			result = await operation()
		except Exception:
			self._on_failure()
			raise
		self._on_success()
		return result

	def _before_call(self) -> None:
		if self.state != CircuitState.OPEN:
			return
		assert self.opened_at is not None
		if self._clock() - self.opened_at < self.recovery_timeout:
			raise CircuitOpenError(f'{self.name} circuit is open')
		self.state = CircuitState.HALF_OPEN
		self.successes = 0

	def _on_success(self) -> None:
		self.failures = 0
		if self.state != CircuitState.HALF_OPEN:
			return
		self.successes += 1
		if self.successes >= self.success_threshold:
			self.state = CircuitState.CLOSED
			self.opened_at = None

	def _on_failure(self) -> None:
		self.successes = 0
		self.failures += 1
		if self.state == CircuitState.HALF_OPEN or self.failures >= self.failure_threshold:
			self.state = CircuitState.OPEN
			self.opened_at = self._clock()
