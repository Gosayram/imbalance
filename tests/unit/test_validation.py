import pytest
from imbalance.core.validation import (
	ValidationError,
	validate_agent,
	validate_budget,
	validate_content,
	validate_link_type,
	validate_section,
	validate_session_id,
	validate_session_status,
	validate_slug,
)


def test_validate_slug_valid():
	assert validate_slug('my-slug') == 'my-slug'
	assert validate_slug('decisions/001-db') == 'decisions/001-db'
	assert validate_slug('context') == 'context'


def test_validate_slug_empty():
	with pytest.raises(ValidationError, match='cannot be empty'):
		validate_slug('')


def test_validate_slug_invalid_chars():
	with pytest.raises(ValidationError, match='Invalid slug'):
		validate_slug('slug with spaces')


def test_validate_slug_too_long():
	with pytest.raises(ValidationError, match='too long'):
		validate_slug('a' * 256)


def test_validate_section_valid():
	assert validate_section('decisions') == 'decisions'
	assert validate_section('context') == 'context'
	assert validate_section('issues') == 'issues'


def test_validate_section_invalid():
	with pytest.raises(ValidationError, match='Invalid section'):
		validate_section('invalid')


def test_validate_link_type_valid():
	assert validate_link_type('references') == 'references'
	assert validate_link_type('related') == 'related'
	assert validate_link_type('depends_on') == 'depends_on'


def test_validate_link_type_invalid():
	with pytest.raises(ValidationError, match='Invalid link type'):
		validate_link_type('invalid')


def test_validate_session_status_valid():
	assert validate_session_status('active') == 'active'
	assert validate_session_status('flushed') == 'flushed'


def test_validate_session_status_invalid():
	with pytest.raises(ValidationError, match='Invalid status'):
		validate_session_status('invalid')


def test_validate_agent_valid():
	assert validate_agent('claude') == 'claude'
	assert validate_agent('codex') == 'codex'


def test_validate_agent_invalid():
	with pytest.raises(ValidationError, match='Invalid agent'):
		validate_agent('invalid')


def test_validate_budget_valid():
	assert validate_budget(100) == 100
	assert validate_budget(2000) == 2000
	assert validate_budget(100000) == 100000


def test_validate_budget_too_low():
	with pytest.raises(ValidationError, match='too low'):
		validate_budget(50)


def test_validate_budget_too_high():
	with pytest.raises(ValidationError, match='too high'):
		validate_budget(100001)


def test_validate_content_valid():
	assert validate_content('hello') == 'hello'
	assert validate_content('  hello  ') == 'hello'


def test_validate_content_empty():
	with pytest.raises(ValidationError, match='cannot be empty'):
		validate_content('')


def test_validate_content_whitespace():
	with pytest.raises(ValidationError, match='cannot be empty'):
		validate_content('   ')


def test_validate_content_too_long():
	with pytest.raises(ValidationError, match='too long'):
		validate_content('a' * 1000001)


def test_validate_session_id_valid():
	assert validate_session_id('abc123') == 'abc123'
	assert validate_session_id('550e8400-e29b-41d4-a716-446655440000') == '550e8400-e29b-41d4-a716-446655440000'


def test_validate_session_id_empty():
	with pytest.raises(ValidationError, match='cannot be empty'):
		validate_session_id('')


def test_validate_session_id_invalid():
	with pytest.raises(ValidationError, match='Invalid session ID'):
		validate_session_id('invalid session!')
