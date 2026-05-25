import pytest
from unittest.mock import AsyncMock, patch
from imbalance.storage.db import checkpoint, integrity_check


@pytest.mark.asyncio
async def test_checkpoint_valid_mode():
	mock_db = AsyncMock()
	await checkpoint(mock_db, "PASSIVE")
	mock_db.execute.assert_called()


@pytest.mark.asyncio
async def test_checkpoint_invalid_mode():
	mock_db = AsyncMock()
	with pytest.raises(ValueError):
		await checkpoint(mock_db, "INVALID")


@pytest.mark.asyncio
async def test_integrity_check_healthy():
	mock_db = AsyncMock()
	mock_cursor = AsyncMock()
	mock_cursor.fetchone.return_value = ["ok"]
	mock_db.execute.return_value = mock_cursor
	result = await integrity_check(mock_db)
	assert result == "ok"


@pytest.mark.asyncio
async def test_integrity_check_no_result():
	mock_db = AsyncMock()
	mock_cursor = AsyncMock()
	mock_cursor.fetchone.return_value = None
	mock_db.execute.return_value = mock_cursor
	with pytest.raises(RuntimeError):
		await integrity_check(mock_db)
