import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from imbalance.core.retry import retry_async, retry_sync, RetryConfig, RetryError


@pytest.mark.asyncio
async def test_retry_async_success():
	call_count = 0

	async def func():
		nonlocal call_count
		call_count += 1
		return 'success'

	result = await retry_async(func)
	assert result == 'success'
	assert call_count == 1


@pytest.mark.asyncio
async def test_retry_async_retry_on_failure():
	call_count = 0

	async def func():
		nonlocal call_count
		call_count += 1
		if call_count < 3:
			raise ValueError('not yet')
		return 'success'

	config = RetryConfig(max_retries=3, base_delay=0.01)
	result = await retry_async(func, config=config)
	assert result == 'success'
	assert call_count == 3


@pytest.mark.asyncio
async def test_retry_async_exhausted():
	async def func():
		raise ValueError('always fail')

	config = RetryConfig(max_retries=2, base_delay=0.01)
	with pytest.raises(RetryError) as exc_info:
		await retry_async(func, config=config)

	assert exc_info.value.attempts == 3
	assert isinstance(exc_info.value.last_exception, ValueError)


@pytest.mark.asyncio
async def test_retry_async_non_retryable():
	call_count = 0

	async def func():
		nonlocal call_count
		call_count += 1
		raise TypeError('non-retryable')

	config = RetryConfig(
		max_retries=3,
		base_delay=0.01,
		retryable_exceptions=(ValueError,),
	)
	with pytest.raises(TypeError):
		await retry_async(func, config=config)

	assert call_count == 1


def test_retry_sync_success():
	call_count = 0

	def func():
		nonlocal call_count
		call_count += 1
		return 'success'

	result = retry_sync(func)
	assert result == 'success'
	assert call_count == 1


def test_retry_sync_retry_on_failure():
	call_count = 0

	def func():
		nonlocal call_count
		call_count += 1
		if call_count < 3:
			raise ValueError('not yet')
		return 'success'

	config = RetryConfig(max_retries=3, base_delay=0.01)
	result = retry_sync(func, config=config)
	assert result == 'success'
	assert call_count == 3


def test_retry_sync_exhausted():
	def func():
		raise ValueError('always fail')

	config = RetryConfig(max_retries=2, base_delay=0.01)
	with pytest.raises(RetryError) as exc_info:
		retry_sync(func, config=config)

	assert exc_info.value.attempts == 3


def test_retry_config_defaults():
	config = RetryConfig()
	assert config.max_retries == 3
	assert config.base_delay == 1.0
	assert config.max_delay == 30.0
	assert config.exponential_base == 2.0


def test_retry_error_message():
	error = RetryError(ValueError('test'), 3)
	assert '3 attempts' in str(error)
	assert 'test' in str(error)
