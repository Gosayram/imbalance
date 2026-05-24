from imbalance.graph.trigram import _extract_trigrams, trigram_search, build_trigram_index
import pytest


def test_extract_trigrams_basic():
	result = _extract_trigrams('hello')
	assert 'hel' in result
	assert 'ell' in result
	assert 'llo' in result
	assert len(result) == 3


def test_extract_trigrams_short_name():
	assert _extract_trigrams('ab') == frozenset()
	assert _extract_trigrams('') == frozenset()


def test_extract_trigrams_case_insensitive():
	result = _extract_trigrams('HandleRequest')
	assert 'han' in result
	assert 'HAN' not in result


def test_extract_trigrams_no_duplicates():
	result = _extract_trigrams('aaaa')
	assert len(result) == 1
	assert 'aaa' in result


@pytest.mark.asyncio
async def test_trigram_search_finds_exact(graph_db):
	await graph_db.execute(
		"INSERT INTO code_symbols(kb_name,name,kind,file_path,line,end_line,signature,language) "
		"VALUES ('test','TokenService','class','auth.py',1,5,'class TokenService','python')"
	)
	await graph_db.commit()

	from imbalance.graph.trigram import build_trigram_index
	rows = await graph_db.execute_fetchall(
		"SELECT id FROM code_symbols WHERE name='TokenService'"
	)
	await build_trigram_index(graph_db, {'TokenService': rows[0]['id']})

	results = await trigram_search(graph_db, 'TokenService', 'test')
	assert len(results) == 1
	assert results[0]['name'] == 'TokenService'


@pytest.mark.asyncio
async def test_trigram_search_partial_match(graph_db):
	await graph_db.execute(
		"INSERT INTO code_symbols(kb_name,name,kind,file_path,line,end_line,signature,language) "
		"VALUES ('test','TokenService','class','auth.py',1,5,'class TokenService','python')"
	)
	await graph_db.commit()
	rows = await graph_db.execute_fetchall(
		"SELECT id FROM code_symbols WHERE name='TokenService'"
	)
	await build_trigram_index(graph_db, {'TokenService': rows[0]['id']})

	results = await trigram_search(graph_db, 'Token', 'test')
	assert any(r['name'] == 'TokenService' for r in results)


@pytest.mark.asyncio
async def test_trigram_search_no_results(graph_db):
	results = await trigram_search(graph_db, 'NonExistentXyz', 'test')
	assert results == []