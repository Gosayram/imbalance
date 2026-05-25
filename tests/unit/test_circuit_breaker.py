import pytest
import time
from imbalance.core.circuit_breaker import CircuitBreaker, CircuitState, CircuitOpenError


def test_circuit_state_values():
	assert CircuitState.CLOSED == "closed"
	assert CircuitState.OPEN == "open"
	assert CircuitState.HALF_OPEN == "half_open"


def test_circuit_breaker_init():
	cb = CircuitBreaker("test")
	assert cb.name == "test"
	assert cb.state == CircuitState.CLOSED


def test_circuit_breaker_invalid_thresholds():
	with pytest.raises(ValueError):
		CircuitBreaker("test", failure_threshold=0)
	with pytest.raises(ValueError):
		CircuitBreaker("test", success_threshold=0)


@pytest.mark.asyncio
async def test_circuit_breaker_success():
	async def success_op():
		return "success"
	cb = CircuitBreaker("test")
	result = await cb.call(success_op)
	assert result == "success"
	assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_failure():
	cb = CircuitBreaker("test", failure_threshold=2)
	async def fail_op():
		raise ValueError("test error")
	for _ in range(2):
		with pytest.raises(ValueError):
			await cb.call(fail_op)
	assert cb.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_circuit_open_error():
	cb = CircuitBreaker("test", failure_threshold=1, recovery_timeout=1.0, clock=lambda: time.monotonic())
	async def fail_op():
		raise ValueError("test error")
	with pytest.raises(ValueError):
		await cb.call(fail_op)
	assert cb.state == CircuitState.OPEN
	with pytest.raises(CircuitOpenError):
		await cb.call(lambda: "test")
