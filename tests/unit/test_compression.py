import pytest
from imbalance.core.compression import compress_context, _truncate


@pytest.mark.asyncio
async def test_compress_context_truncation():
	text = "word " * 100
	result = await compress_context(text, 50)
	assert len(result.split()) <= 50


def test_truncate_short_text():
	text = "hello world"
	assert _truncate(text, 100) == text


def test_truncate_long_text():
	text = " ".join(["word"] * 100)
	result = _truncate(text, 10)
	assert len(result.split()) == 10
