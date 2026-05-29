import pytest
from imbalance.core.secrets import scan_for_secrets, redact_secrets, has_secrets, SECRET_PATTERNS


def test_scan_for_secrets_multiple():
	text = '''
	api_key = "sk-fake-api-key-for-testing-only-not-real-1234567890"
	password = "supersecretpassword123"
	'''
	matches = scan_for_secrets(text)
	assert len(matches) >= 2


def test_scan_for_secrets_database_url():
	text = 'DATABASE_URL = "postgres://user:password@localhost:5432/db"'
	matches = scan_for_secrets(text)
	assert len(matches) > 0
	assert any('Database URL' in m.secret_type for m in matches)


def test_scan_for_secrets_slack_token():
	text = 'slack_token = "xoxb-fake-token-for-testing-only-not-real"'
	matches = scan_for_secrets(text)
	assert len(matches) > 0
	assert any('Slack Token' in m.secret_type for m in matches)


def test_scan_for_secrets_gitlab_token():
	text = 'gitlab_token = "glpat-fake-token-for-testing-only-not-real"'
	matches = scan_for_secrets(text)
	assert len(matches) > 0
	assert any('GitLab Token' in m.secret_type for m in matches)


def test_scan_for_secrets_anthropic_key():
	text = 'anthropic_key = "sk-ant-fake-key-for-testing-only-not-real-1234567890"'
	matches = scan_for_secrets(text)
	assert len(matches) > 0
	assert any('Anthropic Key' in m.secret_type for m in matches)


def test_scan_for_secrets_openrouter_key():
	text = 'openrouter_key = "sk-or-fake-key-for-testing-only-not-real-1234567890"'
	matches = scan_for_secrets(text)
	assert len(matches) > 0
	assert any('OpenRouter Key' in m.secret_type for m in matches)


def test_redact_secrets_multiple():
	text = '''
	api_key = "sk-fake-api-key-for-testing-only-not-real-1234567890"
	password = "supersecretpassword123"
	'''
	redacted, count = redact_secrets(text)
	assert count >= 2
	assert 'REDACTED' in redacted


def test_redact_secrets_preserves_normal_text():
	text = 'This is normal text. api_key = "sk-fake-api-key-for-testing-only-not-real-1234567890"'
	redacted, count = redact_secrets(text)
	assert 'This is normal text.' in redacted
	assert count > 0


def test_has_secrets_multiple():
	text = '''
	api_key = "sk-fake-api-key-for-testing-only-not-real-1234567890"
	password = "supersecretpassword123"
	'''
	assert has_secrets(text) is True


def test_has_secrets_empty():
	assert has_secrets('') is False


def test_secret_patterns_count():
	assert len(SECRET_PATTERNS) == 13
