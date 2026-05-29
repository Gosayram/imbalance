import pytest
from imbalance.core.secrets import scan_for_secrets, redact_secrets, has_secrets


def test_scan_for_secrets_api_key():
	text = 'api_key = "sk-abc123def456ghi789jkl012mno345pqr678stu901vwx234"'
	matches = scan_for_secrets(text)
	assert len(matches) > 0
	assert any('API Key' in m.secret_type for m in matches)


def test_scan_for_secrets_github_token():
	text = 'token = "ghp_abc123def456ghi789jkl012mno345pqr678"'
	matches = scan_for_secrets(text)
	assert len(matches) > 0
	assert any('GitHub Token' in m.secret_type for m in matches)


def test_scan_for_secrets_aws_key():
	text = 'access_key = "AKIAIOSFODNN7EXAMPLE"'
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
	text = 'openai_key = "sk-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567"'
	matches = scan_for_secrets(text)
	assert len(matches) > 0
	assert any('OpenAI Key' in m.secret_type for m in matches)


def test_redact_secrets():
	text = 'api_key = "sk-abc123def456ghi789jkl012mno345pqr678stu901vwx234"'
	redacted, count = redact_secrets(text)
	assert count > 0
	assert 'REDACTED' in redacted
	assert 'sk-abc123def456ghi789jkl012mno345pqr678stu901vwx234' not in redacted


def test_redact_secrets_custom_replacement():
	text = 'api_key = "sk-abc123def456ghi789jkl012mno345pqr678stu901vwx234"'
	redacted, count = redact_secrets(text, replacement='[HIDDEN]')
	assert count > 0
	assert '[HIDDEN]' in redacted


def test_has_secrets_true():
	text = 'api_key = "sk-abc123def456ghi789jkl012mno345pqr678stu901vwx234"'
	assert has_secrets(text) is True


def test_has_secrets_false():
	text = 'This is a normal text.'
	assert has_secrets(text) is False
