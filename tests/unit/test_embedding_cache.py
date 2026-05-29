import pytest
from imbalance.core.embedding_cache import EmbeddingCache, get_embedding_cache, set_embedding_cache


def test_cache_put_and_get():
	cache = EmbeddingCache(maxsize=100)
	cache.put('hello', 'model1', [1.0, 2.0, 3.0])

	result = cache.get('hello', 'model1')
	assert result == [1.0, 2.0, 3.0]


def test_cache_miss():
	cache = EmbeddingCache(maxsize=100)
	result = cache.get('nonexistent', 'model1')
	assert result is None


def test_cache_different_models():
	cache = EmbeddingCache(maxsize=100)
	cache.put('hello', 'model1', [1.0, 2.0])
	cache.put('hello', 'model2', [3.0, 4.0])

	assert cache.get('hello', 'model1') == [1.0, 2.0]
	assert cache.get('hello', 'model2') == [3.0, 4.0]


def test_cache_eviction():
	cache = EmbeddingCache(maxsize=2)
	cache.put('a', 'm', [1.0])
	cache.put('b', 'm', [2.0])
	cache.put('c', 'm', [3.0])

	assert cache.get('a', 'm') is None
	assert cache.get('b', 'm') == [2.0]
	assert cache.get('c', 'm') == [3.0]


def test_cache_lru_order():
	cache = EmbeddingCache(maxsize=2)
	cache.put('a', 'm', [1.0])
	cache.put('b', 'm', [2.0])

	# Access 'a' to make it recently used
	cache.get('a', 'm')

	# Add 'c' - should evict 'b' (least recently used)
	cache.put('c', 'm', [3.0])

	assert cache.get('a', 'm') == [1.0]
	assert cache.get('b', 'm') is None
	assert cache.get('c', 'm') == [3.0]


def test_cache_size():
	cache = EmbeddingCache(maxsize=100)
	assert cache.size == 0

	cache.put('a', 'm', [1.0])
	assert cache.size == 1

	cache.put('b', 'm', [2.0])
	assert cache.size == 2


def test_cache_hit_rate():
	cache = EmbeddingCache(maxsize=100)
	cache.put('a', 'm', [1.0])

	# 1 hit, 0 misses
	cache.get('a', 'm')
	assert cache.hit_rate == 1.0

	# 1 hit, 1 miss
	cache.get('b', 'm')
	assert cache.hit_rate == 0.5


def test_cache_stats():
	cache = EmbeddingCache(maxsize=100)
	cache.put('a', 'm', [1.0])
	cache.get('a', 'm')
	cache.get('b', 'm')

	stats = cache.stats
	assert stats['size'] == 1
	assert stats['maxsize'] == 100
	assert stats['hits'] == 1
	assert stats['misses'] == 1
	assert stats['hit_rate'] == 0.5


def test_cache_clear():
	cache = EmbeddingCache(maxsize=100)
	cache.put('a', 'm', [1.0])
	cache.get('a', 'm')

	cache.clear()
	assert cache.size == 0
	assert cache.hit_rate == 0.0


def test_get_embedding_cache_singleton():
	cache1 = get_embedding_cache()
	cache2 = get_embedding_cache()
	assert cache1 is cache2


def test_set_embedding_cache():
	custom = EmbeddingCache(maxsize=500)
	set_embedding_cache(custom)
	assert get_embedding_cache() is custom
