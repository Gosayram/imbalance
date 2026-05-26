import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Mock the mcp module before importing
mock_types = MagicMock()
mock_types.Tool = MagicMock()
mock_types.ToolAnnotations = MagicMock()

def make_text_content(**kwargs):
	mock = MagicMock()
	mock.type = kwargs.get('type', 'text')
	mock.text = kwargs.get('text', '')
	return mock

def make_resource(**kwargs):
	mock = MagicMock()
	mock.uri = kwargs.get('uri', '')
	mock.name = kwargs.get('name', '')
	mock.description = kwargs.get('description', '')
	mock.mimeType = kwargs.get('mimeType', '')
	return mock

mock_types.TextContent = MagicMock(side_effect=make_text_content)
mock_types.ImageContent = MagicMock()
mock_types.EmbeddedResource = MagicMock()
mock_types.Resource = MagicMock(side_effect=make_resource)

sys.modules['mcp'] = MagicMock()
sys.modules['mcp.server'] = MagicMock()
sys.modules['mcp.server.stdio'] = MagicMock()
sys.modules['mcp.types'] = mock_types
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


@pytest.mark.asyncio
async def test_get_status():
	from imbalance.mcp.server import _get_status
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(side_effect=[
		[{'cnt': 5}],
		[{'cnt': 10}]
	])
	result = await _get_status(db, "test_kb")
	assert len(result) == 1


@pytest.mark.asyncio
async def test_list_topics():
	from imbalance.mcp.server import _list_topics
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[
		{'section': 'decisions', 'slug': 'test-slug'},
		{'section': 'context', 'slug': 'another'}
	])
	result = await _list_topics(db, "test_kb")
	assert len(result) == 1


@pytest.mark.asyncio
async def test_list_topics_empty():
	from imbalance.mcp.server import _list_topics
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[])
	result = await _list_topics(db, "test_kb")
	assert len(result) == 1


@pytest.mark.asyncio
async def test_resume_session_missing_session_id():
	from imbalance.mcp.server import _resume_session
	db = AsyncMock()
	db.execute = AsyncMock()
	db.commit = AsyncMock()
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	# Test that the function raises when session_id is missing
	try:
		await _resume_session(db, project, {})
		assert False, "Should have raised ValueError"
	except ValueError as e:
		assert "session_id required" in str(e)


@pytest.mark.asyncio
async def test_save_compaction_summary_missing_session_id():
	from imbalance.mcp.server import _save_compaction_summary
	db = AsyncMock()
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	await _save_compaction_summary(db, project, {'session_id': 'test-id'})
	db.commit.assert_called()


@pytest.mark.asyncio
async def test_save_compaction_summary_with_content():
	from imbalance.mcp.server import _save_compaction_summary
	db = AsyncMock()
	db.execute = AsyncMock()
	db.commit = AsyncMock()
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	await _save_compaction_summary(db, project, {
		'session_id': 'abc123',
		'summary': 'test summary',
		'decisions': ['dec1', 'dec2'],
	})
	db.commit.assert_called()






