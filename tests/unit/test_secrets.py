import pytest
from imbalance.core.secrets import scan_for_secrets, redact_secrets, has_secrets


def test_scan_for_secrets_api_key():
	text = 'api_key = "sk-fake-api-key-for-testing-only-not-real-1234567890"'
	matches = scan_for_secrets(text)
	assert len(matches) > 0
	assert any('API Key' in m.secret_type for m in matches)


def test_scan_for_secrets_github_token():
	text = 'token = "ghp_TEST_TOKEN_NOT_REAL_1234567890abcdefghijklmnop"'
	matches = scan_for_secrets(text)
	assert len(matches) > 0
	assert any('GitHub Token' in m.secret_type for m in matches)


def test_scan_for_secrets_aws_key():
	text = 'access_key = "AKIAFAKEKEYEXAMPLE1234"'
	matches = scan_for_secrets(text)
	assert len(matches) > 0
	assert any('AWS Access Key' in m.secret_type for m in matches)


def test_scan_for_secrets_jwt():
	text = 'token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"'
	matches = scan_for_secrets(text)
	assert len(matches) > 0
	assert any('JWT Token' in m.secret_type for m in matches)


def test_scan_for_secrets_private_key():
	text = '-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA...'
	matches = scan_for_secrets(text)
	assert len(matches) > 0
	assert any('Private Key' in m.secret_type for m in matches)


def test_scan_for_secrets_password():
	text = 'password = "supersecretpassword123"'
	matches = scan_for_secrets(text)
	assert len(matches) > 0
	assert any('Password' in m.secret_type for m in matches)


def test_scan_for_secrets_no_secrets():
	text = 'This is a normal text without any secrets.'
	matches = scan_for_secrets(text)
	assert len(matches) == 0


def test_scan_for_secrets_openai_key():
	text = 'openai_key = "sk-abcdefghijklmnopqrstuvwxyz1234567890abcdefghijklmn"'
	matches = scan_for_secrets(text)
	assert len(matches) > 0
	assert any('OpenAI Key' in m.secret_type for m in matches)


def test_redact_secrets():
	text = 'api_key = "sk-fake-api-key-for-testing-only-not-real-1234567890"'
	redacted, count = redact_secrets(text)
	assert count > 0
	assert 'REDACTED' in redacted
	assert 'sk-fake-api-key-for-testing-only-not-real-1234567890' not in redacted


def test_redact_secrets_custom_replacement():
	text = 'api_key = "sk-fake-api-key-for-testing-only-not-real-1234567890"'
	redacted, count = redact_secrets(text, replacement='[HIDDEN]')
	assert count > 0
	assert '[HIDDEN]' in redacted


def test_has_secrets_true():
	text = 'api_key = "sk-fake-api-key-for-testing-only-not-real-1234567890"'
	assert has_secrets(text) is True


def test_has_secrets_false():
	text = 'This is a normal text.'
	assert has_secrets(text) is False
