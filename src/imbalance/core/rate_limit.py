from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class RateLimitConfig:
	"""Rate limit configuration."""
	requests: int = 100
	window_seconds: int = 60


@dataclass
class RateLimitState:
	"""Rate limit state for a key."""
	requests: list[float] = field(default_factory=list)


class RateLimiter:
	"""Simple in-memory rate limiter using sliding window."""

	def __init__(self, config: RateLimitConfig | None = None) -> None:
		self.config = config or RateLimitConfig()
		self._state: dict[str, RateLimitState] = defaultdict(RateLimitState)

	def is_allowed(self, key: str) -> bool:
		"""Check if request is allowed.

		Args:
			key: Rate limit key (e.g., IP address, user ID)

		Returns:
			True if request is allowed
		"""
		now = time.monotonic()
		state = self._state[key]

		# Remove expired requests
		cutoff = now - self.config.window_seconds
		state.requests = [t for t in state.requests if t > cutoff]

		# Check limit
		if len(state.requests) >= self.config.requests:
			return False

		# Add current request
		state.requests.append(now)
		return True

	def get_remaining(self, key: str) -> int:
		"""Get remaining requests for key.

		Args:
			key: Rate limit key

		Returns:
			Number of remaining requests
		"""
		now = time.monotonic()
		state = self._state[key]

		# Remove expired requests
		cutoff = now - self.config.window_seconds
		state.requests = [t for t in state.requests if t > cutoff]

		return max(0, self.config.requests - len(state.requests))

	def get_reset_time(self, key: str) -> float:
		"""Get time until rate limit resets.

		Args:
			key: Rate limit key

		Returns:
			Seconds until reset
		"""
		state = self._state[key]
		if not state.requests:
			return 0.0

		oldest = min(state.requests)
		reset_time = oldest + self.config.window_seconds - time.monotonic()
		return max(0.0, reset_time)

	def reset(self, key: str) -> None:
		"""Reset rate limit for key.

		Args:
			key: Rate limit key
		"""
		self._state.pop(key, None)

	def reset_all(self) -> None:
		"""Reset all rate limits."""
		self._state.clear()


# Global rate limiter instance
_global_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
	"""Get global rate limiter instance."""
	global _global_limiter
	if _global_limiter is None:
		_global_limiter = RateLimiter()
	return _global_limiter


def set_rate_limiter(limiter: RateLimiter) -> None:
	"""Set global rate limiter instance."""
	global _global_limiter
	_global_limiter = limiter
