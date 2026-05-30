import pytest
import time
from unittest.mock import patch
from imbalance.core.rate_limit import RateLimiter, RateLimitConfig


def test_rate_limiter_allows_requests():
	limiter = RateLimiter(RateLimitConfig(requests=3, window_seconds=60))

	assert limiter.is_allowed('user1') is True
	assert limiter.is_allowed('user1') is True
	assert limiter.is_allowed('user1') is True


def test_rate_limiter_blocks_excess():
	limiter = RateLimiter(RateLimitConfig(requests=2, window_seconds=60))

	assert limiter.is_allowed('user1') is True
	assert limiter.is_allowed('user1') is True
	assert limiter.is_allowed('user1') is False


def test_rate_limiter_different_keys():
	limiter = RateLimiter(RateLimitConfig(requests=1, window_seconds=60))

	assert limiter.is_allowed('user1') is True
	assert limiter.is_allowed('user2') is True
	assert limiter.is_allowed('user1') is False


def test_rate_limiter_window_reset():
	config = RateLimitConfig(requests=2, window_seconds=1)
	limiter = RateLimiter(config)

	assert limiter.is_allowed('user1') is True
	assert limiter.is_allowed('user1') is True
	assert limiter.is_allowed('user1') is False

	# Wait for window to reset
	time.sleep(1.1)

	assert limiter.is_allowed('user1') is True


def test_rate_limiter_get_remaining():
	limiter = RateLimiter(RateLimitConfig(requests=3, window_seconds=60))

	assert limiter.get_remaining('user1') == 3
	limiter.is_allowed('user1')
	assert limiter.get_remaining('user1') == 2
	limiter.is_allowed('user1')
	assert limiter.get_remaining('user1') == 1


def test_rate_limiter_get_reset_time():
	limiter = RateLimiter(RateLimitConfig(requests=1, window_seconds=60))

	limiter.is_allowed('user1')
	reset_time = limiter.get_reset_time('user1')
	assert reset_time > 0
	assert reset_time <= 60


def test_rate_limiter_reset():
	limiter = RateLimiter(RateLimitConfig(requests=1, window_seconds=60))

	assert limiter.is_allowed('user1') is True
	assert limiter.is_allowed('user1') is False

	limiter.reset('user1')
	assert limiter.is_allowed('user1') is True


def test_rate_limiter_reset_all():
	limiter = RateLimiter(RateLimitConfig(requests=1, window_seconds=60))

	assert limiter.is_allowed('user1') is True
	assert limiter.is_allowed('user2') is True

	limiter.reset_all()
	assert limiter.is_allowed('user1') is True
	assert limiter.is_allowed('user2') is True
