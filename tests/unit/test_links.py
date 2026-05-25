import pytest
from unittest.mock import AsyncMock
from imbalance.core.links import create_link, remove_link, get_links, expand_links


@pytest.mark.asyncio
async def test_create_link():
	db = AsyncMock()
	await create_link(db, "kb", "source", "target", "references")
	db.execute.assert_called()
	db.commit.assert_called()


@pytest.mark.asyncio
async def test_remove_link():
	db = AsyncMock()
	await remove_link(db, "kb", "source", "target", "references")
	db.execute.assert_called()
	db.commit.assert_called()


@pytest.mark.asyncio
async def test_get_links():
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[])
	result = await get_links(db, "kb", "source")
	assert result == []


@pytest.mark.asyncio
async def test_expand_links_empty():
	db = AsyncMock()
	result = await expand_links(db, "kb", [])
	assert result == {}


@pytest.mark.asyncio
async def test_expand_links_with_slugs():
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[])
	result = await expand_links(db, "kb", ["slug1"])
	assert result == {}