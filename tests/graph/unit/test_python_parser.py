import pytest
from imbalance.graph.parser import PythonASTParser
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