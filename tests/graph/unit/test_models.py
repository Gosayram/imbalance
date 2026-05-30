import pytest
from dataclasses import FrozenInstanceError
from imbalance.graph.models import Symbol


def test_symbol_is_frozen():
	sym = Symbol(
		name='hello',
		kind='function',
		file_path='test.py',
		line=1,
		end_line=1,
		signature='def hello()',
		language='python',
	)
	with pytest.raises(FrozenInstanceError):
		sym.name = 'changed'


def test_symbol_uses_slots():
	sym = Symbol(
		name='hello',
		kind='function',
		file_path='test.py',
		line=1,
		end_line=1,
		signature='def hello()',
		language='python',
	)
	assert not hasattr(sym, '__dict__')


def test_symbol_defaults():
	sym = Symbol(
		name='test',
		kind='function',
		file_path='test.py',
		line=1,
		end_line=5,
		signature='def test()',
		language='python',
	)
	assert sym.name == 'test'
	assert sym.kind == 'function'


def test_symbol_equality():
	sym1 = Symbol(name='test', kind='function', file_path='a.py', line=1, end_line=1, signature='', language='py')
	sym2 = Symbol(name='test', kind='function', file_path='a.py', line=1, end_line=1, signature='', language='py')
	assert sym1 == sym2


def test_symbol_inequality():
	sym1 = Symbol(name='test', kind='function', file_path='a.py', line=1, end_line=1, signature='', language='py')
	sym2 = Symbol(name='other', kind='function', file_path='a.py', line=1, end_line=1, signature='', language='py')
	assert sym1 != sym2