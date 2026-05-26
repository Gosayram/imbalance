import pytest


@pytest.mark.asyncio
async def test_full_index_creates_symbols(python_project, graph_db):
	from imbalance.graph.indexer import GraphIndexer
	indexer = GraphIndexer(python_project, graph_db, 'test')
	stats = await indexer.index_full()
	assert stats.symbols > 0
	assert stats.files > 0


@pytest.mark.asyncio
async def test_full_index_skips_syntax_errors(python_project, graph_db):
	from imbalance.graph.indexer import GraphIndexer
	indexer = GraphIndexer(python_project, graph_db, 'test')
	stats = await indexer.index_full()
	assert stats is not None
	assert stats.symbols > 0
