from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SecretMatch:
	"""Detected secret in text."""
	secret_type: str
	value: str
	start: int
	end: int


# Common secret patterns
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
	('API Key', re.compile(r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?')),
	('AWS Access Key', re.compile(r'AKIA[0-9A-Z]{16}')),
	('AWS Secret Key', re.compile(r'(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*["\']?([a-zA-Z0-9/+=]{40})["\']?')),
	('GitHub Token', re.compile(r'gh[pousr]_[A-Za-z0-9_]{36,}')),
	('GitLab Token', re.compile(r'glpat-[A-Za-z0-9_\-]{20,}')),
	('Slack Token', re.compile(r'xox[bpsorta]-[A-Za-z0-9\-]+')),
	('JWT Token', re.compile(r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}')),
	('Private Key', re.compile(r'-----BEGIN\s+(RSA|EC|DSA|OPENSSH)\s+PRIVATE\s+KEY-----')),
	('Password', re.compile(r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?([^\s"\']{8,})["\']?')),
	('Database URL', re.compile(r'(?i)(postgres|mysql|mongodb|redis)://[^\s]+')),
	('OpenAI Key', re.compile(r'sk-[A-Za-z0-9]{48,}')),
	('Anthropic Key', re.compile(r'sk-ant-[A-Za-z0-9_\-]{40,}')),
	('OpenRouter Key', re.compile(r'sk-or-[A-Za-z0-9_\-]{40,}')),
]


def scan_for_secrets(text: str) -> list[SecretMatch]:
	"""Scan text for potential secrets.

	Args:
		text: Text to scan

	Returns:
		List of detected secrets
	"""
	matches: list[SecretMatch] = []

	for secret_type, pattern in SECRET_PATTERNS:
		for match in pattern.finditer(text):
			matches.append(SecretMatch(
				secret_type=secret_type,
				value=match.group(0)[:20] + '...',  # Truncate for safety
				start=match.start(),
				end=match.end(),
			))

	return matches


def redact_secrets(text: str, replacement: str = '[REDACTED]') -> tuple[str, int]:
	"""Redact secrets from text.

	Args:
		text: Text to redact
		replacement: Replacement string

	Returns:
		Tuple of (redacted_text, number_of_redactions)
	"""
	redacted = text
	count = 0

	for _, pattern in SECRET_PATTERNS:
		redacted, n = pattern.subn(replacement, redacted)
		count += n

	return redacted, count


def has_secrets(text: str) -> bool:
	"""Check if text contains potential secrets.

	Args:
		text: Text to check

	Returns:
		True if secrets detected
	"""
	return bool(scan_for_secrets(text))
