import pytest


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_search_after_data_insertion(db, sample_project):
    """Search should find newly inserted data."""
    from imbalance.core.query import QueryEngine
    from imbalance.storage.store import SQLiteStore

    store = SQLiteStore(db, kb_name="test-kb")

    # Insert test data
    await store.upsert_section(
        slug="context",
        section="context",
        content="We are using Redis for rate limiting",
        token_count=12,
    )

    engine = QueryEngine(store=store)
    result = await engine.get_context_pack(
        query="Redis rate limiting",
        budget_tokens=2000,
    )
    assert result is not None


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_search_with_scope_filter(db_with_data, sample_project):
    """Search with scope should filter results."""
    from imbalance.core.query import QueryEngine
    from imbalance.storage.store import SQLiteStore

    store = SQLiteStore(db_with_data, kb_name="test-kb")
    engine = QueryEngine(store=store)

    result = await engine.get_context_pack(
        query="PostgreSQL",
        budget_tokens=2000,
        scope=["decisions"],
    )
    assert result is not None
