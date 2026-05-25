import pytest
from unittest.mock import patch
from imbalance.core.tokens import estimate_tokens


def test_estimate_tokens_empty():
	assert estimate_tokens('') == 0
	assert estimate_tokens('   ') == 0


def test_estimate_tokens_simple():
	with patch('imbalance.core.tokens._get_encoding') as mock_enc:
		mock_enc.return_value.encode.return_value = [1, 2, 3]
		result = estimate_tokens('hello world')
		assert result == 3


def test_estimate_tokens_fallback():
	from imbalance.core.tokens import estimate_tokens
	with patch('imbalance.core.tokens._get_encoding') as mock_enc:
		mock_enc.side_effect = Exception('error')
		result = estimate_tokens('hello world')
		assert result == 2  # Fallback to word count


def test_estimate_tokens_single_word_fallback():
	with patch('imbalance.core.tokens._get_encoding') as mock_enc:
		mock_enc.side_effect = Exception('error')
		result = estimate_tokens('hello')
		assert result == 1