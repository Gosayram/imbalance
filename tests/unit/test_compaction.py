import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from imbalance.core.compaction import CompactionReport, smart_merge_section, KBCompactor


def test_compaction_report_defaults():
	report = CompactionReport()
	assert report.archived == []
	assert report.updated == []
	assert report.evergreen == []
	assert report.current == []


def test_compaction_report_with_data():
	report = CompactionReport(archived=["old"], updated=["new"])
	assert "old" in report.archived
	assert "new" in report.updated


@pytest.mark.asyncio
async def test_smart_merge_section_empty_existing():
	mock_router = MagicMock()
	mock_router.complete = AsyncMock()
	mock_db = AsyncMock()
	mock_db.execute = AsyncMock(return_value=[])
	mock_db.commit = AsyncMock()

	result = await smart_merge_section(mock_router, "kb1", "slug1", "", "new content", db=mock_db)
	assert result == "new content"


@pytest.mark.asyncio
async def test_kb_compactor_init():
	mock_db = MagicMock()
	mock_router = MagicMock()
	compactor = KBCompactor(mock_db, mock_router, "test_kb")
	assert compactor.kb_name == "test_kb"


@pytest.mark.asyncio
async def test_smart_merge_section_with_existing():
	mock_router = MagicMock()
	mock_router.complete = AsyncMock(return_value="merged content")
	mock_db = AsyncMock()

	result = await smart_merge_section(mock_router, "kb1", "slug1", "old content", "new content", db=mock_db)
	assert result == "merged content"


@pytest.mark.asyncio
async def test_smart_merge_section_no_db():
	mock_router = MagicMock()
	mock_router.complete = AsyncMock(return_value="merged")

	result = await smart_merge_section(mock_router, "kb1", "slug1", "old", "new", db=None)
	assert result == "merged"
