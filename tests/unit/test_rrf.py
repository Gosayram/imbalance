from __future__ import annotations

from imbalance.core.context import ContextChunk
from imbalance.core.query import rrf_merge


def _chunk(slug: str, section: str = 'context', score: float = 0.5) -> ContextChunk:
	return ContextChunk(
		slug=slug, section=section, content=f'content-{slug}', score=score, token_count=10
	)


def test_rrf_merge_combines_fts_and_vec():
	fts = [_chunk('a'), _chunk('b'), _chunk('c')]
	vec = [_chunk('b'), _chunk('d')]
	result = rrf_merge(fts, vec)
	slugs = [c.slug for c in result]
	assert 'b' in slugs
	assert 'a' in slugs
	assert 'd' in slugs
	assert slugs.index('b') < slugs.index('a')


def test_rrf_merge_empty_inputs():
	assert rrf_merge([], []) == []
	assert len(rrf_merge([_chunk('a')], [])) == 1
	assert len(rrf_merge([], [_chunk('a')])) == 1


def test_rrf_merge_scope_weights():
	fts = [_chunk('x', 'decisions'), _chunk('y', 'context')]
	vec = [_chunk('x', 'decisions')]
	weights = {'decisions': 2.0, 'context': 0.5}
	result = rrf_merge(fts, vec, scope_weights=weights)
	slugs = [c.slug for c in result]
	assert slugs[0] == 'x'


def test_rrf_merge_deduplicates():
	fts = [_chunk('a'), _chunk('b')]
	vec = [_chunk('a'), _chunk('b')]
	result = rrf_merge(fts, vec)
	slugs = [c.slug for c in result]
	assert len(slugs) == 2
	assert set(slugs) == {'a', 'b'}


def test_rrf_merge_ordering():
	fts = [_chunk('c', 'decisions', 0.1), _chunk('a', 'decisions', 0.9), _chunk('b', 'context', 0.5)]
	vec = [_chunk('c', 'decisions', 0.2)]
	result = rrf_merge(fts, vec)
	assert len(result) == 3


def test_rrf_merge_single_source():
	fts = [_chunk('a', 'decisions'), _chunk('b', 'context'), _chunk('c', 'stack')]
	result = rrf_merge(fts, [])
	assert len(result) == 3
