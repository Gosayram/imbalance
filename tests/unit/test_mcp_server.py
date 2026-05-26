import pytest
import sys
from unittest.mock import MagicMock, AsyncMock, patch

# Mock the mcp module before importing
sys.modules['mcp'] = MagicMock()
sys.modules['mcp.server'] = MagicMock()
sys.modules['mcp.server.stdio'] = MagicMock()
sys.modules['mcp.types'] = MagicMock()
sys.modules['mcp.server.models'] = MagicMock()
sys.modules['mcp.server.notification'] = MagicMock()

from imbalance.mcp.server import AgentType, detect_agent, format_for_agent


def test_detect_agent_claude():
	assert detect_agent("claudecode", "") == AgentType.CLAUDE
	assert detect_agent("anything", "claude") == AgentType.CLAUDE


def test_detect_agent_cursor():
	assert detect_agent("cursor", "") == AgentType.CURSOR


def test_detect_agent_codex():
	assert detect_agent("codex", "") == AgentType.CODEX


def test_detect_agent_gemini():
	assert detect_agent("gemini", "") == AgentType.GEMINI


def test_detect_agent_unknown():
	assert detect_agent("unknown", "") == AgentType.UNKNOWN
	assert detect_agent("", "") == AgentType.UNKNOWN


def test_format_for_agent_claude():
	result = format_for_agent(AgentType.CLAUDE, "test content")
	assert result == "test content"


def test_format_for_agent_cursor():
	lines = "\n".join([f"line {i}" for i in range(20)])
	result = format_for_agent(AgentType.CURSOR, lines)
	assert "..." in result


def test_format_for_agent_cursor_short():
	result = format_for_agent(AgentType.CURSOR, "short")
	assert "..." not in result


def test_format_for_agent_codex():
	lines = ["short line", "a" * 200]
	result = format_for_agent(AgentType.CODEX, "\n".join(lines))
	assert "<line>" in result


def test_agent_type_values():
	assert AgentType.CLAUDE.value == "claude"
	assert AgentType.CURSOR.value == "cursor"


def test_agent_type_all():
	assert AgentType.CLAUDE == AgentType.CLAUDE
	assert AgentType.CODEX == AgentType.CODEX
	assert AgentType.GEMINI == AgentType.GEMINI


def test_format_for_agent_codex_short_line():
	result = format_for_agent(AgentType.CODEX, "short")
	assert "<line>short</line>" == result


def test_format_for_agent_cursor_many_lines():
	lines = [f"line {i}" for i in range(15)]
	result = format_for_agent(AgentType.CURSOR, "\n".join(lines))
	assert "..." in result


def test_format_for_agent_gemini():
	result = format_for_agent(AgentType.GEMINI, "test content")
	assert result == "test content"


def test_format_for_agent_cursor_exactly_10_lines():
	lines = [f"line {i}" for i in range(10)]
	result = format_for_agent(AgentType.CURSOR, "\n".join(lines))
	assert "..." not in result


def test_format_for_agent_cursor_11_lines():
	lines = [f"line {i}" for i in range(11)]
	result = format_for_agent(AgentType.CURSOR, "\n".join(lines))
	assert "..." in result


def test_format_for_agent_codex_all_long_lines():
	lines = [f"line {i}" * 100 for i in range(20)]
	result = format_for_agent(AgentType.CODEX, "\n".join(lines))
	assert result.count("<line>") >= 15
