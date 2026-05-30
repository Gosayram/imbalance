import pytest
from unittest.mock import AsyncMock
from imbalance.core.batch import batch_upsert_sections, batch_create_links, batch_archive_sections, BatchResult


def test_batch_result():
	result = BatchResult(total=10, success=8, failed=2, errors=['error1', 'error2'])
	assert result.total == 10
	assert result.success == 8
	assert result.failed == 2
	assert len(result.errors) == 2


@pytest.mark.asyncio
async def test_batch_upsert_sections_empty():
	db = AsyncMock()
	db.executemany = AsyncMock()
	db.commit = AsyncMock()

	result = await batch_upsert_sections(db, 'test-kb', [])

	assert result.total == 0
	assert result.success == 0
	assert result.failed == 0


@pytest.mark.asyncio
async def test_batch_create_links_empty():
	db = AsyncMock()
	db.executemany = AsyncMock()
	db.commit = AsyncMock()

	result = await batch_create_links(db, 'test-kb', [])

	assert result.total == 0
	assert result.success == 0
	assert result.failed == 0


@pytest.mark.asyncio
async def test_batch_archive_sections_empty():
	db = AsyncMock()
	db.executemany = AsyncMock()
	db.commit = AsyncMock()

	result = await batch_archive_sections(db, 'test-kb', [])

	assert result.total == 0
	assert result.success == 0
	assert result.failed == 0


@pytest.mark.asyncio
async def test_batch_upsert_sections_large_batch():
	db = AsyncMock()
	db.executemany = AsyncMock()
	db.commit = AsyncMock()

	sections = [
		{'slug': f'section/{i}', 'section': 'decisions', 'content': f'content {i}'}
		for i in range(250)
	]

	result = await batch_upsert_sections(db, 'test-kb', sections, batch_size=100)

	assert result.total == 250
	assert result.success == 250
	assert result.failed == 0
	assert db.executemany.call_count == 3  # 250 / 100 = 3 batches


@pytest.mark.asyncio
async def test_batch_create_links_large_batch():
	db = AsyncMock()
	db.executemany = AsyncMock()
	db.commit = AsyncMock()

	links = [
		{'source_slug': f'src/{i}', 'target_slug': f'tgt/{i}', 'link_type': 'references'}
		for i in range(150)
	]

	result = await batch_create_links(db, 'test-kb', links, batch_size=50)

	assert result.total == 150
	assert result.success == 150
	assert result.failed == 0
	assert db.executemany.call_count == 3  # 150 / 50 = 3 batches


@pytest.mark.asyncio
async def test_batch_archive_sections_with_reason():
	db = AsyncMock()
	db.executemany = AsyncMock()
	db.commit = AsyncMock()

	slugs = ['decisions/001', 'decisions/002']

	result = await batch_archive_sections(db, 'test-kb', slugs, reason='obsolete')

	assert result.total == 2
	assert result.success == 2
	assert result.failed == 0
