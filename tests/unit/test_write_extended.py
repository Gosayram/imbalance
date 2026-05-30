import pytest
from unittest.mock import AsyncMock, MagicMock
from imbalance.core.write import WriteEngine, SaveResult, machine_id, _default_slug


def test_save_result():
	result = SaveResult(slug='test', section_id=1, token_count=100, secrets_redacted=0)
	assert result.slug == 'test'
	assert result.section_id == 1
	assert result.token_count == 100
	assert result.secrets_redacted == 0


def test_save_result_with_secrets():
	result = SaveResult(slug='test', section_id=1, token_count=100, secrets_redacted=3)
	assert result.secrets_redacted == 3


def test_machine_id():
	mid = machine_id()
	assert ':' in mid
	assert len(mid) > 0


def test_default_slug_stack():
	assert _default_slug('stack') == 'stack'


def test_default_slug_context():
	assert _default_slug('context') == 'context'


def test_default_slug_issues():
	assert _default_slug('issues') == 'issues'


def test_default_slug_decisions():
	slug = _default_slug('decisions')
	assert slug.startswith('decisions/')
	assert len(slug) > len('decisions/')


def test_default_slug_unique():
	slug1 = _default_slug('decisions')
	slug2 = _default_slug('decisions')
	assert slug1 != slug2


@pytest.mark.asyncio
async def test_write_engine_save_fact_with_secret():
	store = AsyncMock()
	store.kb_name = 'test-kb'
	store.upsert_section = AsyncMock(return_value=1)

	engine = WriteEngine(store, redact_secrets=True)
	result = await engine.save_fact(
		content='api_key = "sk-fake-api-key-for-testing-only-not-real-1234567890"',
		section='context',
	)

	assert result.secrets_redacted > 0
	assert 'REDACTED' not in result.slug  # Slug should not be affected


@pytest.mark.asyncio
async def test_write_engine_save_fact_no_secret():
	store = AsyncMock()
	store.kb_name = 'test-kb'
	store.upsert_section = AsyncMock(return_value=1)

	engine = WriteEngine(store, redact_secrets=True)
	result = await engine.save_fact(
		content='This is normal content without secrets.',
		section='context',
	)

	assert result.secrets_redacted == 0


@pytest.mark.asyncio
async def test_write_engine_save_fact_redact_disabled():
	store = AsyncMock()
	store.kb_name = 'test-kb'
	store.upsert_section = AsyncMock(return_value=1)

	engine = WriteEngine(store, redact_secrets=False)
	result = await engine.save_fact(
		content='api_key = "sk-fake-api-key-for-testing-only-not-real-1234567890"',
		section='context',
	)

	assert result.secrets_redacted == 0
