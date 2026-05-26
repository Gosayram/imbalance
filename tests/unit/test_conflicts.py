import pytest
from unittest.mock import AsyncMock, MagicMock
from imbalance.core.conflicts import detect_conflict, mark_conflict, get_conflicts, ConflictResult
import aiosqlite


@pytest.fixture
async def db(tmp_path):
	db_path = tmp_path / "test.db"
	db = await aiosqlite.connect(db_path)
	db.row_factory = aiosqlite.Row
	await db.execute("""
		CREATE TABLE IF NOT EXISTS wiki_sections (
			id INTEGER PRIMARY KEY, slug TEXT, content TEXT, kb_name TEXT,
			section TEXT, archived INTEGER, created_at TEXT
		)
	""")
	await db.execute("""
		CREATE TABLE IF NOT EXISTS kb_links (
			kb_name TEXT, source_slug TEXT, target_slug TEXT, link_type TEXT,
			created_at TEXT, UNIQUE(kb_name, source_slug, target_slug, link_type)
		)
	""")
	await db.commit()
	yield db
	await db.close()


@pytest.mark.asyncio
async def test_detect_conflict_no_existing(db):
	result = await detect_conflict(db, "kb1", "slug1", "new content")
	assert result.conflict is False


@pytest.mark.asyncio
async def test_detect_conflict_with_existing(db):
	await db.execute("INSERT INTO wiki_sections (slug, content, kb_name, section, archived) VALUES (?, ?, ?, ?, 0)",
		("old_slug", "old content", "kb1", "decisions"))
	await db.commit()
	mock_router = MagicMock()
	mock_router.complete = AsyncMock(return_value='{"conflict": true, "conflicting_slug": "old_slug", "reason": "test"}')
	result = await detect_conflict(db, "kb1", "new_slug", "new content", router=mock_router)
	assert result.conflict is True


@pytest.mark.asyncio
async def test_mark_conflict(db):
	await mark_conflict(db, "kb1", "slug1", "slug2", "test reason")
	count = await db.execute_fetchall("SELECT COUNT(*) as cnt FROM kb_links WHERE kb_name='kb1'")
	assert count[0][0] == 2  # Two links created


@pytest.mark.asyncio
async def test_get_conflicts_empty(db):
	result = await get_conflicts(db, "kb1")
	assert result == []


@pytest.mark.asyncio
async def test_get_conflicts_with_data(db):
	await db.execute("INSERT INTO kb_links (kb_name, source_slug, target_slug, link_type, created_at) VALUES (?, ?, ?, ?, ?)",
		("kb1", "a", "b", "conflicts", "2024-01-01"))
	await db.commit()
	result = await get_conflicts(db, "kb1")
	assert len(result) == 1


@pytest.mark.asyncio
async def test_detect_conflict_no_router(db):
	await db.execute("INSERT INTO wiki_sections (slug, content, kb_name, section, archived) VALUES (?, ?, ?, ?, 0)",
		("old_slug", "old content", "kb1", "decisions"))
	await db.commit()
	# No router provided but there are existing decisions - should return False
	result = await detect_conflict(db, "kb1", "new_slug", "new content", router=None)
	assert result.conflict is False


@pytest.mark.asyncio
async def test_detect_conflict_invalid_json(db):
	await db.execute("INSERT INTO wiki_sections (slug, content, kb_name, section, archived) VALUES (?, ?, ?, ?, 0)",
		("old_slug", "old content", "kb1", "decisions"))
	await db.commit()
	mock_router = MagicMock()
	mock_router.complete = AsyncMock(return_value='invalid json response')
	result = await detect_conflict(db, "kb1", "new_slug", "new content", router=mock_router)
	assert result.conflict is False


@pytest.mark.asyncio
async def test_detect_conflict_router_error(db):
	await db.execute("INSERT INTO wiki_sections (slug, content, kb_name, section, archived) VALUES (?, ?, ?, ?, 0)",
		("old_slug", "old content", "kb1", "decisions"))
	await db.commit()
	mock_router = MagicMock()
	mock_router.complete = AsyncMock(side_effect=Exception("LLM error"))
	result = await detect_conflict(db, "kb1", "new_slug", "new content", router=mock_router)
	assert result.conflict is False
