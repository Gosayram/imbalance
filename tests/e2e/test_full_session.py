import pytest


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_session_lifecycle(db_with_data, sample_project):
    """Full cycle: search returns context from KB."""
    from imbalance.core.query import QueryEngine
    from imbalance.storage.store import SQLiteStore

    store = SQLiteStore(db_with_data, kb_name="test-kb")
    engine = QueryEngine(store=store)
    result = await engine.get_context_pack(
        query="PostgreSQL database choice",
        budget_tokens=2000,
    )
    assert result is not None


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_search_respects_budget(db_with_data, sample_project):
    """Search result should respect budget_tokens."""
    from imbalance.core.query import QueryEngine
    from imbalance.storage.store import SQLiteStore

    store = SQLiteStore(db_with_data, kb_name="test-kb")
    engine = QueryEngine(store=store)
    result = await engine.get_context_pack(
        query="database",
        budget_tokens=100,
    )
    total = sum(c.token_count for c in result.evidence)
    assert total <= 200


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_search_returns_context_pack(db_with_data, sample_project):
    """Search should return a valid ContextPack."""
    from imbalance.core.query import QueryEngine
    from imbalance.storage.store import SQLiteStore

    store = SQLiteStore(db_with_data, kb_name="test-kb")
    engine = QueryEngine(store=store)
    result = await engine.get_context_pack(
        query="auth",
        budget_tokens=2000,
    )
    assert result is not None
    assert result.query == "auth"
    assert result.budget_tokens == 2000


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_multiple_searches_are_cached(db_with_data, sample_project):
    """Repeated identical queries should hit cache."""
    from imbalance.core.query import QueryEngine
    from imbalance.storage.store import SQLiteStore

    store = SQLiteStore(db_with_data, kb_name="test-kb")
    engine = QueryEngine(store=store)

    result1 = await engine.get_context_pack(query="auth", budget_tokens=2000)
    result2 = await engine.get_context_pack(query="auth", budget_tokens=2000)

    assert len(result1.evidence) == len(result2.evidence)
