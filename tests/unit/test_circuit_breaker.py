import pytest
import time
from unittest.mock import AsyncMock
from imbalance.core.circuit_breaker import CircuitBreaker, CircuitOpenError


@pytest.mark.asyncio
async def test_circuit_breaker_success():
	cb = CircuitBreaker(name="test")
	async def success_func():
		return "result"
	result = await cb.call(success_func)
	assert result == "result"


@pytest.mark.asyncio
async def test_circuit_breaker_open_error():
	cb = CircuitBreaker(name="test", failure_threshold=1)
	async def fail_func():
		raise Exception("error")
	async def success_func():
		return "result"
	
	# First failure
	with pytest.raises(Exception):
		await cb.call(fail_func)
	
	# Circuit should be open now
	with pytest.raises(CircuitOpenError):
		await cb.call(success_func)


@pytest.mark.asyncio
async def test_circuit_breaker_not_open_on_success():
	cb = CircuitBreaker(name="test")
	async def success_func():
		return "result"
	
	# Multiple successes
	for _ in range(3):
		await cb.call(success_func)
	
	# Circuit should still be closed
	assert cb.state == "closed"


def test_circuit_state_values():
	cb = CircuitBreaker(name="test")
	assert cb.state == "closed"
