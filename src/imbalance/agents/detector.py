from __future__ import annotations

import shutil
from pathlib import Path


def _is_claude_installed() -> bool:
	"""Check if Claude Code is installed."""
	return shutil.which('claude') is not None


def _is_codex_installed() -> bool:
	"""Check if Codex CLI is installed."""
	return (Path.home() / '.codex').exists() or shutil.which('codex') is not None


def _is_cursor_installed() -> bool:
	"""Check if Cursor is installed."""
	cursor_config = Path.home() / '.cursor'
	cursor_bin = shutil.which('cursor')
	return cursor_config.exists() or cursor_bin is not None


def _is_gemini_installed() -> bool:
	"""Check if Gemini CLI is installed."""
	return shutil.which('gemini') is not None


def _is_windsurf_installed() -> bool:
	"""Check if Windsurf is installed."""
	return (Path.home() / '.windsurf').exists()


def _is_cline_installed() -> bool:
	"""Check if Cline (Claude Dev) VS Code extension is installed."""
	vscode_extensions = Path.home() / '.vscode' / 'extensions'
	if not vscode_extensions.exists():
		return False
	return any(vscode_extensions.glob('saoudrizwan.claude-dev*'))


def _is_copilot_installed() -> bool:
	"""Check if GitHub Copilot is installed."""
	return (Path.home() / '.github' / 'copilot-instructions.md').exists()


AGENT_DETECTORS = {
	'claude': _is_claude_installed,
	'codex': _is_codex_installed,
	'cursor': _is_cursor_installed,
	'gemini': _is_gemini_installed,
	'windsurf': _is_windsurf_installed,
	'cline': _is_cline_installed,
	'copilot': _is_copilot_installed,
}


def detect_installed_agents() -> list[str]:
	"""Detect installed coding agents on this machine."""
	return [name for name, check in AGENT_DETECTORS.items() if check()]
