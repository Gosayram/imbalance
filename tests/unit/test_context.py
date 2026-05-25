import pytest
from imbalance.core.context import ContextMode, ContextChunk, ContextPack


def test_context_mode_values():
	assert ContextMode.OFF.value == "off"
	assert ContextMode.READ_ONLY.value == "read_only"
	assert ContextMode.WRITE_ONLY.value == "write_only"
	assert ContextMode.READ_WRITE.value == "read_write"


def test_context_chunk():
	chunk = ContextChunk(slug="test-slug", section="overview", content="content", score=0.9, token_count=100)
	assert chunk.slug == "test-slug"
	assert chunk.score == 0.9


def test_context_pack_render():
	pack = ContextPack(
		query="test",
		budget_tokens=2000,
		precedence=["wiki"],
		summary="test summary",
		evidence=[ContextChunk(slug="s", section="sec", content="c", score=0.5, token_count=10)],
	)
	result = pack.render_markdown()
	assert "<context-pack>" in result
	assert "<memory-summary>" in result
	assert "<evidence" in result


def test_context_pack_render_no_summary():
	pack = ContextPack(
		query="test",
		budget_tokens=2000,
		precedence=["wiki"],
		summary=None,
		evidence=[],
	)
	result = pack.render_markdown()
	assert "<context-pack>" in result
	assert "<memory-summary>" not in result


def test_context_pack_render_with_warnings():
	pack = ContextPack(
		query="test",
		budget_tokens=2000,
		precedence=["wiki"],
		summary=None,
		evidence=[],
		warnings=["test warning"],
	)
	result = pack.render_markdown()
	assert "<warnings>" in result


def test_context_pack_render_with_omitted():
	pack = ContextPack(
		query="test",
		budget_tokens=2000,
		precedence=["wiki"],
		summary=None,
		evidence=[],
		omitted=["file1.py", "file2.py"],
	)
	result = pack.render_markdown()
	assert "<context-pack>" in result


def test_context_chunk_defaults():
	chunk = ContextChunk(slug="s", section="sec", content="c", score=0.5, token_count=10)
	assert chunk.confidence == 0.5


def test_context_chunk_custom_confidence():
	chunk = ContextChunk(slug="s", section="sec", content="c", score=0.5, token_count=10, confidence=0.8)
	assert chunk.confidence == 0.8
