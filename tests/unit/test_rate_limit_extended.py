import pytest
import time
from imbalance.core.rate_limit import RateLimiter, RateLimitConfig, get_rate_limiter, set_rate_limiter


def test_rate_limiter_default_config():
	limiter = RateLimiter()
	assert limiter.config.requests == 100
	assert limiter.config.window_seconds == 60


def test_rate_limiter_custom_config():
	config = RateLimitConfig(requests=10, window_seconds=30)
	limiter = RateLimiter(config)
	assert limiter.config.requests == 10
	assert limiter.config.window_seconds == 30


def test_rate_limiter_multiple_keys():
	limiter = RateLimiter(RateLimitConfig(requests=2, window_seconds=60))

	assert limiter.is_allowed('key1') is True
	assert limiter.is_allowed('key1') is True
	assert limiter.is_allowed('key1') is False

	assert limiter.is_allowed('key2') is True
	assert limiter.is_allowed('key2') is True
	assert limiter.is_allowed('key2') is False


def test_rate_limiter_get_remaining():
	limiter = RateLimiter(RateLimitConfig(requests=5, window_seconds=60))

	assert limiter.get_remaining('key') == 5
	limiter.is_allowed('key')
	assert limiter.get_remaining('key') == 4
	limiter.is_allowed('key')
	assert limiter.get_remaining('key') == 3


def test_rate_limiter_get_reset_time_no_requests():
	limiter = RateLimiter(RateLimitConfig(requests=5, window_seconds=60))
	assert limiter.get_reset_time('key') == 0.0


def test_rate_limiter_get_reset_time_with_requests():
	limiter = RateLimiter(RateLimitConfig(requests=1, window_seconds=60))
	limiter.is_allowed('key')

	reset_time = limiter.get_reset_time('key')
	assert reset_time > 0
	assert reset_time <= 60


def test_rate_limiter_reset():
	limiter = RateLimiter(RateLimitConfig(requests=1, window_seconds=60))

	assert limiter.is_allowed('key') is True
	assert limiter.is_allowed('key') is False

	limiter.reset('key')
	assert limiter.is_allowed('key') is True


def test_rate_limiter_reset_all():
	limiter = RateLimiter(RateLimitConfig(requests=1, window_seconds=60))

	limiter.is_allowed('key1')
	limiter.is_allowed('key2')

	limiter.reset_all()

	assert limiter.is_allowed('key1') is True
	assert limiter.is_allowed('key2') is True


def test_get_rate_limiter_singleton():
	limiter1 = get_rate_limiter()
	limiter2 = get_rate_limiter()
	assert limiter1 is limiter2


def test_set_rate_limiter():
	custom = RateLimiter(RateLimitConfig(requests=50, window_seconds=30))
	set_rate_limiter(custom)
	assert get_rate_limiter() is custom
