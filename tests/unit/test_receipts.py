import pytest
from imbalance.storage.receipts import ToolResultReceipts


@pytest.fixture
async def db(tmp_path):
	db_path = tmp_path / "test.db"
	import aiosqlite
	db = await aiosqlite.connect(db_path)
	await db.execute("""
		CREATE TABLE IF NOT EXISTS tool_result_receipts (
			id TEXT PRIMARY KEY,
			session_id TEXT,
			tool_name TEXT,
			content_hash TEXT,
			preview TEXT,
			bytes INTEGER,
			ref_path TEXT
		)
	""")
	await db.commit()
	return db


@pytest.mark.asyncio
async def test_tool_result_receipts_store(db):
	store = ToolResultReceipts(db)
	receipt_id = await store.store(
		session_id="session-123",
		tool_name="test_tool",
		content="test content for receipt"
	)
	assert receipt_id.startswith("tr_")
