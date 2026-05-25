import pytest
from unittest.mock import patch
from imbalance.core.tokens import estimate_tokens


def test_estimate_tokens_empty():
	assert estimate_tokens("") == 0


def test_estimate_tokens_whitespace():
	assert estimate_tokens("   ") == 0


def test_estimate_tokens_basic():
	result = estimate_tokens("hello world")
	assert result > 0


def test_estimate_tokens_fallback():
	with patch('imbalance.core.tokens._get_encoding') as mock_enc:
		mock_enc.side_effect = Exception("test")
		result = estimate_tokens("hello world")
		assert result == 2  # word count fallback
