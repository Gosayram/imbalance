from __future__ import annotations

import re

# Slug pattern: alphanumeric, hyphens, underscores, slashes
SLUG_PATTERN = re.compile(r'^[a-zA-Z0-9_/-]+$')

# Section names
VALID_SECTIONS = {'decisions', 'context', 'stack', 'issues', 'about', 'patterns'}

# Link types
VALID_LINK_TYPES = {'references', 'related', 'depends_on', 'supersedes', 'conflicts'}

# Session statuses
VALID_SESSION_STATUSES = {'active', 'pending_flush', 'flushed', 'failed'}

# Agent names
VALID_AGENTS = {'claude', 'codex', 'cursor', 'gemini', 'windsurf', 'copilot'}


class ValidationError(Exception):
	"""Validation error."""


def validate_slug(slug: str) -> str:
	"""Validate and return slug."""
	if not slug:
		raise ValidationError('Slug cannot be empty')
	if not SLUG_PATTERN.match(slug):
		raise ValidationError(f'Invalid slug: {slug}. Use alphanumeric, hyphens, underscores, slashes')
	if len(slug) > 255:
		raise ValidationError(f'Slug too long: {len(slug)} > 255')
	return slug


def validate_section(section: str) -> str:
	"""Validate section name."""
	if section not in VALID_SECTIONS:
		raise ValidationError(f'Invalid section: {section}. Use: {", ".join(sorted(VALID_SECTIONS))}')
	return section


def validate_link_type(link_type: str) -> str:
	"""Validate link type."""
	if link_type not in VALID_LINK_TYPES:
		raise ValidationError(f'Invalid link type: {link_type}. Use: {", ".join(sorted(VALID_LINK_TYPES))}')
	return link_type


def validate_session_status(status: str) -> str:
	"""Validate session status."""
	if status not in VALID_SESSION_STATUSES:
		raise ValidationError(f'Invalid status: {status}. Use: {", ".join(sorted(VALID_SESSION_STATUSES))}')
	return status


def validate_agent(agent: str) -> str:
	"""Validate agent name."""
	if agent not in VALID_AGENTS:
		raise ValidationError(f'Invalid agent: {agent}. Use: {", ".join(sorted(VALID_AGENTS))}')
	return agent


def validate_budget(budget: int) -> int:
	"""Validate budget tokens."""
	if budget < 100:
		raise ValidationError(f'Budget too low: {budget} < 100')
	if budget > 100_000:
		raise ValidationError(f'Budget too high: {budget} > 100,000')
	return budget


def validate_content(content: str) -> str:
	"""Validate content."""
	if not content or not content.strip():
		raise ValidationError('Content cannot be empty')
	if len(content) > 1_000_000:
		raise ValidationError(f'Content too long: {len(content)} > 1,000,000')
	return content.strip()


def validate_session_id(session_id: str) -> str:
	"""Validate session ID format."""
	if not session_id:
		raise ValidationError('Session ID cannot be empty')
	# UUID format or prefix
	if not re.match(r'^[a-f0-9-]+$', session_id):
		raise ValidationError(f'Invalid session ID: {session_id}')
	return session_id
