import pytest
from imbalance.core.links import create_link, remove_link, get_links, expand_links
import aiosqlite


@pytest.fixture
async def db(tmp_path):
	db_path = tmp_path / "test.db"
	db = await aiosqlite.connect(db_path)
	db.row_factory = aiosqlite.Row
	await db.execute("""
		CREATE TABLE kb_links (
			kb_name TEXT, source_slug TEXT, target_slug TEXT, link_type TEXT,
			created_at TEXT, UNIQUE(kb_name, source_slug, target_slug, link_type)
		)
	""")
	await db.commit()
	yield db
	await db.close()


@pytest.mark.asyncio
async def test_create_link(db):
	await create_link(db, "kb1", "source", "target", "references")
	rows = await db.execute_fetchall("SELECT * FROM kb_links WHERE kb_name='kb1'")
	assert len(rows) == 1


@pytest.mark.asyncio
async def test_remove_link(db):
	await create_link(db, "kb1", "source", "target", "references")
	await remove_link(db, "kb1", "source", "target", "references")
	rows = await db.execute_fetchall("SELECT * FROM kb_links")
	assert len(rows) == 0


@pytest.mark.asyncio
async def test_get_links(db):
	await create_link(db, "kb1", "slug1", "slug2", "references")
	await create_link(db, "kb1", "slug1", "slug3", "related")
	result = await get_links(db, "kb1", "slug1")
	assert len(result) == 2


@pytest.mark.asyncio
async def test_expand_links(db):
	await create_link(db, "kb1", "slug1", "slug2", "references")
	result = await expand_links(db, "kb1", ["slug1"])
	assert "slug2" in result


@pytest.mark.asyncio
async def test_expand_links_empty(db):
	result = await expand_links(db, "kb1", [])
	assert result == {}
