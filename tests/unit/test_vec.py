import pytest
from unittest.mock import AsyncMock, patch
from imbalance.storage.vec import is_vec_available, ensure_vec_table, _floats_to_blob


@pytest.mark.asyncio
async def test_is_vec_available_not_available():
	mock_db = AsyncMock()
	mock_db.enable_load_extension = AsyncMock()
	with patch.dict('sys.modules', {'sqlite_vec': None}):
		result = await is_vec_available(mock_db)
		assert result is False


def test_floats_to_blob():
	result = _floats_to_blob([1.0, 2.0, 3.0])
	assert len(result) == 12  # 3 floats * 4 bytes each


def test_floats_to_blob_empty():
	result = _floats_to_blob([])
	assert result == b''
