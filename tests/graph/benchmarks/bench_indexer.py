import asyncio
import random
import string
import time
import pytest


@pytest.fixture
def populated_db(graph_db):
	async def _populate():
		await graph_db.executemany(
			"INSERT INTO code_symbols(kb_name,name,kind,file_path,line,end_line,signature,language) VALUES (?,?,?,?,?,?,?,?)",
			[('bench', ''.join(random.choices(string.ascii_letters, k=random.randint(5, 20))), 'function', f'file_{i}.py', i, i + 1, '', 'python') for i in range(1000)],
		)
		await graph_db.commit()
		rows = await graph_db.execute_fetchall('SELECT id, name FROM code_symbols WHERE kb_name=?', ('bench',))
		return {r['name']: r['id'] for r in rows}
	return asyncio.get_event_loop().run_until_complete(_populate())


@pytest.mark.asyncio
async def test_bench_trigram_search(graph_db, populated_db):
	from imbalance.graph.trigram import build_trigram_index, trigram_search
	await build_trigram_index(graph_db, populated_db)
	names = list(populated_db.keys())
	query = names[0][:6]
	start = time.perf_counter()
	for _ in range(100):
		await trigram_search(graph_db, query, 'bench')
	elapsed = (time.perf_counter() - start) / 100
	print(f'\ntrigram search: {elapsed*1000:.2f}ms per query')
	assert elapsed < 0.05
