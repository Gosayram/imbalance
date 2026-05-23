import pytest

from imbalance.core.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitState


@pytest.mark.asyncio
async def test_circuit_opens_after_failure_threshold() -> None:
	breaker = CircuitBreaker('provider', failure_threshold=2)

	async def fail() -> None:
		raise ConnectionError('down')

	for _ in range(2):
		with pytest.raises(ConnectionError):
			await breaker.call(fail)

	assert breaker.state == CircuitState.OPEN
	with pytest.raises(CircuitOpenError):
		await breaker.call(fail)


@pytest.mark.asyncio
async def test_half_open_requires_successes_to_close() -> None:
	now = 0.0
	breaker = CircuitBreaker(
		'provider',
		failure_threshold=1,
		recovery_timeout=5,
		success_threshold=2,
		clock=lambda: now,
	)

	async def fail() -> None:
		raise ConnectionError('down')

	async def succeed() -> str:
		return 'ok'

	with pytest.raises(ConnectionError):
		await breaker.call(fail)

	now = 6.0
	assert await breaker.call(succeed) == 'ok'
	assert breaker.state == CircuitState.HALF_OPEN
	assert await breaker.call(succeed) == 'ok'
	assert breaker.state == CircuitState.CLOSED
