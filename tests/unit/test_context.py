from imbalance.core.context import ContextChunk, ContextPack


def test_context_pack_renders_structured_markdown() -> None:
	pack = ContextPack(
		query="auth",
		budget_tokens=2000,
		precedence=["current_task", "memory_summary", "wiki_sections"],
		summary="Project uses SQLite-first memory.",
		evidence=[
			ContextChunk(
				slug="decisions/001-db",
				section="decisions",
				content="Use SQLite WAL.",
				score=0.1,
				token_count=4,
				confidence=0.8,
			)
		],
	)

	rendered = pack.render_markdown()

	assert "<context-pack>" in rendered
	assert "<memory-summary>" in rendered
	assert 'slug="decisions/001-db"' in rendered
