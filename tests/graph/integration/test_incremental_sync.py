import pytest


@pytest.mark.asyncio
async def test_full_index_populates_trigrams(python_project, graph_db):
	from imbalance.graph.indexer import GraphIndexer
	indexer = GraphIndexer(python_project, graph_db, 'test')
	await indexer.index_full()
	trigrams = await graph_db.execute_fetchall('SELECT COUNT(*) AS cnt FROM trigram_index')
	assert trigrams[0]['cnt'] > 0
