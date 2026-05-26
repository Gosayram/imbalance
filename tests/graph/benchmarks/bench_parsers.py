import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / 'fixtures'


@pytest.fixture
def python_source():
	return (FIXTURES_DIR / 'python_samples' / 'classes.py').read_bytes()


@pytest.fixture
def ts_source():
	return (FIXTURES_DIR / 'typescript_samples' / 'interfaces.ts').read_bytes()


def test_bench_python_parser(benchmark, python_source):
	from imbalance.graph.parser import PythonASTParser
	parser = PythonASTParser()
	result = benchmark(parser.parse, python_source, 'bench.py')
	assert len(result) > 0


def test_bench_pattern_parser_typescript(benchmark, ts_source):
	from imbalance.graph.parser import CompiledPatternParser
	parser = CompiledPatternParser()
	result = benchmark(parser.parse, ts_source, 'bench.ts', 'typescript')
	assert len(result) > 0


def test_bench_extract_trigrams(benchmark):
	from imbalance.graph.trigram import _extract_trigrams
	result = benchmark(_extract_trigrams, 'TokenRotationService')
	assert len(result) > 0
