import pytest


@pytest.mark.asyncio
async def test_parser_no_memory_leak(memory_tracker, python_project):
	from imbalance.graph.parser import FileParser
	parser = FileParser()
	auth_py = str(python_project / 'src' / 'auth.py')

	with memory_tracker:
		for _ in range(1000):
			symbols = parser.parse(auth_py)
			del symbols

	memory_tracker.assert_no_leak(threshold_kb=200)
