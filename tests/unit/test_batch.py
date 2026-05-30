import pytest
from unittest.mock import AsyncMock
from imbalance.core.batch import batch_upsert_sections, batch_create_links, batch_archive_sections


@pytest.mark.asyncio
async def test_batch_upsert_sections():
	db = AsyncMock()
	db.executemany = AsyncMock()
	db.commit = AsyncMock()

	sections = [
		{'slug': 'decisions/001', 'section': 'decisions', 'content': 'test content 1'},
		{'slug': 'decisions/002', 'section': 'decisions', 'content': 'test content 2'},
	]

	result = await batch_upsert_sections(db, 'test-kb', sections)

	assert result.total == 2
	assert result.success == 2
	assert result.failed == 0
	assert result.errors == []


@pytest.mark.asyncio
async def test_batch_upsert_sections_error():
	db = AsyncMock()
	db.executemany = AsyncMock(side_effect=Exception('DB error'))
	db.commit = AsyncMock()

	sections = [
		{'slug': 'decisions/001', 'section': 'decisions', 'content': 'test content'},
	]

	result = await batch_upsert_sections(db, 'test-kb', sections)

	assert result.total == 1
	assert result.success == 0
	assert result.failed == 1
	assert len(result.errors) == 1


@pytest.mark.asyncio
async def test_batch_create_links():
	db = AsyncMock()
	db.executemany = AsyncMock()
	db.commit = AsyncMock()

	links = [
		{'source_slug': 'decisions/001', 'target_slug': 'stack/001', 'link_type': 'references'},
		{'source_slug': 'decisions/002', 'target_slug': 'issues/001', 'link_type': 'related'},
	]

	result = await batch_create_links(db, 'test-kb', links)

	assert result.total == 2
	assert result.success == 2
	assert result.failed == 0


@pytest.mark.asyncio
async def test_batch_archive_sections():
	db = AsyncMock()
	db.executemany = AsyncMock()
	db.commit = AsyncMock()

	slugs = ['decisions/001', 'decisions/002', 'decisions/003']

	result = await batch_archive_sections(db, 'test-kb', slugs, reason='obsolete')

	assert result.total == 3
	assert result.success == 3
	assert result.failed == 0


@pytest.mark.asyncio
async def test_batch_upsert_sections_batch_size():
	db = AsyncMock()
	db.executemany = AsyncMock()
	db.commit = AsyncMock()

	sections = [
		{'slug': f'decisions/{i:03d}', 'section': 'decisions', 'content': f'content {i}'}
		for i in range(5)
	]

	result = await batch_upsert_sections(db, 'test-kb', sections, batch_size=2)

	assert result.total == 5
	assert result.success == 5
	assert db.executemany.call_count == 3  # 5 items / batch_size 2 = 3 batches
