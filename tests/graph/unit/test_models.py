import pytest
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
	with pytest.raises(Exception):
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