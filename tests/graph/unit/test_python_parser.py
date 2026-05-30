import pytest
from imbalance.graph.parser import PythonASTParser, FileParser, CompiledPatternParser, _get_patterns
from imbalance.graph.models import Symbol


@pytest.fixture
def parser():
	return PythonASTParser()


def test_parses_simple_function(parser):
	src = b'def hello(x, y): pass'
	symbols = parser.parse(src, 'test.py')
	assert len(symbols) == 1
	assert symbols[0].name == 'hello'
	assert symbols[0].kind == 'function'
	assert symbols[0].line == 1


def test_parses_class_with_methods(parser):
	src = b"""
class TokenService:
	def rotate(self): pass
	async def invalidate(self, user_id): pass
"""
	symbols = parser.parse(src, 'test.py')
	names = {s.name for s in symbols}
	assert 'TokenService' in names
	assert 'rotate' in names
	assert 'invalidate' in names

	rotate = next(s for s in symbols if s.name == 'rotate')
	assert rotate.kind == 'function'


def test_parses_async_function(parser):
	src = b'async def fetch_data(url: str) -> dict: ...'
	symbols = parser.parse(src, 'test.py')
	assert symbols[0].name == 'fetch_data'
	assert symbols[0].kind == 'async_function'


def test_parses_decorated_function(parser):
	src = b"""
@app.route('/users')
@require_auth
def get_users(): pass
"""
	symbols = parser.parse(src, 'test.py')
	assert any(s.name == 'get_users' for s in symbols)


def test_handles_syntax_error_gracefully(parser):
	src = b'def broken('
	symbols = parser.parse(src, 'broken.py')
	assert symbols == ()


def test_handles_empty_file(parser):
	assert parser.parse(b'', 'empty.py') == ()


def test_symbol_is_frozen(parser):
	src = b'def hello(): pass'
	sym = parser.parse(src, 'test.py')[0]
	with pytest.raises(Exception):
		sym.name = 'changed'


def test_symbol_uses_slots(parser):
	src = b'def hello(): pass'
	sym = parser.parse(src, 'test.py')[0]
	assert not hasattr(sym, '__dict__')


def test_file_parser_python():
	fp = FileParser()
	# Test with a real temp file
	import tempfile
	import os
	with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
		f.write('def test_func():\n    pass\n')
		f.flush()
		symbols = fp.parse(f.name)
		assert any(s.name == 'test_func' for s in symbols)
		os.unlink(f.name)


def test_file_parser_javascript(tmp_path):
	from pathlib import Path
	test_file = tmp_path / "test.js"
	test_file.write_text("function hello() { return 1; }")
	fp = FileParser()
	symbols = fp.parse(str(test_file))
	assert any(s.name == 'hello' for s in symbols)


def test_file_parser_typescript(tmp_path):
	from pathlib import Path
	test_file = tmp_path / "test.ts"
	test_file.write_text("function hello() { return 1; }")
	fp = FileParser()
	symbols = fp.parse(str(test_file))
	assert any(s.name == 'hello' for s in symbols)


def test_file_parser_go(tmp_path):
	from pathlib import Path
	test_file = tmp_path / "test.go"
	test_file.write_text("func main() { println() }")
	fp = FileParser()
	symbols = fp.parse(str(test_file))
	assert any(s.name == 'main' for s in symbols)


def test_file_parser_missing_file():
	fp = FileParser()
	symbols = fp.parse('/nonexistent/file.py')
	assert symbols == ()


def test_get_patterns_unknown():
	patterns = _get_patterns('unknown_lang')
	assert patterns == []


def test_parses_nested_class(parser):
	src = b"""
class Outer:
	class Inner:
		def method(self): pass
"""
	symbols = parser.parse(src, 'test.py')
	names = {s.name for s in symbols}
	assert 'Outer' in names
	assert 'Inner' in names


def test_parses_imports(parser):
	src = b'import os\nfrom sys import path'
	symbols = parser.parse(src, 'test.py')
	# imports are not parsed as symbols, just verify no crash
	assert isinstance(symbols, tuple)


def test_compiled_pattern_parser_utf8_error():
	parser = CompiledPatternParser()
	# This should return empty tuple on decode error
	src = b'\xff\xfe'  # Invalid UTF-8
	symbols = parser.parse(src, 'test.py', 'python')
	assert symbols == ()


def test_get_patterns_javascript():
	patterns = _get_patterns('javascript')
	assert len(patterns) == 4


def test_get_patterns_go():
	patterns = _get_patterns('go')
	assert len(patterns) == 3


def test_file_parser_unknown_language(tmp_path):
	test_file = tmp_path / "test.rust"
	test_file.write_text("fn main() {}")
	fp = FileParser()
	symbols = fp.parse(str(test_file))
	assert symbols == ()


def test_get_patterns_python_cache_miss():
	# Clear cache to force cache miss path
	import imbalance.graph.parser as parser_module
	parser_module._PATTERN_CACHE.pop('python', None)
	patterns = _get_patterns('python')
	assert len(patterns) == 3