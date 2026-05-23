from __future__ import annotations


def estimate_tokens(text: str) -> int:
	"""Cheap deterministic token estimate used before tiktoken is wired in."""
	if not text:
		return 0
	return max(1, len(text.split()))
