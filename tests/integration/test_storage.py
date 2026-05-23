from pathlib import Path

import pytest

from imbalance.core.query import QueryEngine
from imbalance.core.write import WriteEngine
from imbalance.storage.db import integrity_check, open_db, run_migrations
from imbalance.storage.store import SQLiteStore


@pytest.mark.asyncio
async def test_migrations_and_fts_context_pack(tmp_path: Path) -> None:
	db = await open_db(tmp_path / "kb.db")
	await run_migrations(db)
	store = SQLiteStore(db, "test-kb")

	await store.upsert_memory_summary("Current work: auth refresh tests.", token_count=6)
	await WriteEngine(store).save_fact(
		content="Use SQLite WAL for reliable local writes.",
		section="decisions",
		slug="decisions/sqlite-wal",
		tags=["sqlite", "reliability"],
	)

	pack = await QueryEngine(store).get_context_pack("SQLite WAL", budget_tokens=2000)

	assert pack.summary == "Current work: auth refresh tests."
	assert [chunk.slug for chunk in pack.evidence] == ["decisions/sqlite-wal"]
	assert await integrity_check(db) == "ok"
	await db.close()


@pytest.mark.asyncio
async def test_upsert_creates_history_and_updates_fts(tmp_path: Path) -> None:
	db = await open_db(tmp_path / "kb.db")
	await run_migrations(db)
	store = SQLiteStore(db, "test-kb")

	await store.upsert_section(
		slug="context",
		section="context",
		content="Implement auth middleware.",
		token_count=3,
	)
	await store.upsert_section(
		slug="context",
		section="context",
		content="Implement billing middleware.",
		token_count=3,
	)

	auth_results = await store.fts_search("auth")
	billing_results = await store.fts_search("billing")
	history = await db.execute_fetchall(
		"SELECT change_type FROM wiki_history WHERE kb_name=? AND slug=? ORDER BY id",
		("test-kb", "context"),
	)

	assert auth_results == []
	assert [row["change_type"] for row in history] == ["create", "update"]
	assert [chunk.slug for chunk in billing_results] == ["context"]
	await db.close()
