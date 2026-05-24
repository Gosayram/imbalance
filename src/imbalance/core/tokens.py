from __future__ import annotations

_encoding = None


def _get_encoding():
	global _encoding
	if _encoding is None:
		import tiktoken

		_encoding = tiktoken.get_encoding('cl100k_base')
	return _encoding


def estimate_tokens(text: str) -> int:
	if not text or not text.strip():
		return 0
	try:
		return len(_get_encoding().encode(text))
	except Exception:
		return max(1, len(text.split()))
