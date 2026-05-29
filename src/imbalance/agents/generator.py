from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from imbalance.agents.detector import detect_installed_agents
from imbalance.core.project import Project


class GeneratorResult(BaseModel):
	"""Result of generating an agent file."""
	agent: Literal['codex', 'claude', 'cursor', 'gemini', 'windsurf', 'copilot']
	path: Path
	mode: Literal['created', 'updated', 'linked', 'skipped']
	managed: bool


MANAGED_MARKER = '<!-- managed by imbalance -->'
SECTION_START = '<!-- imbalance:start -->'
SECTION_END = '<!-- imbalance:end -->'


class AgentFileGenerator:
	"""Base class for agent file generators."""

	def __init__(self, project: Project) -> None:
		self.project = project

	def render(self) -> str:
		"""Render the content for this agent file."""
		raise NotImplementedError

	def target_path(self, cwd: Path) -> Path:
		"""Return the target path for this agent file."""
		raise NotImplementedError

	def _is_managed(self, path: Path) -> bool:
		"""Check if file was created by imbalance."""
		if not path.exists():
			return False
		return MANAGED_MARKER in path.read_text(encoding='utf-8')

	def _wrap_section(self, content: str) -> str:
		"""Wrap content in imbalance section markers."""
		return f'{SECTION_START}\n{content}\n{SECTION_END}'

	def _update_section(self, path: Path, new_content: str) -> str:
		"""Update existing file's imbalance section."""
		existing = path.read_text(encoding='utf-8')
		wrapped = self._wrap_section(new_content)
		if SECTION_START in existing:
			return re.sub(
				rf'{re.escape(SECTION_START)}.*?{re.escape(SECTION_END)}',
				wrapped,
				existing,
				flags=re.DOTALL,
			)
		return existing + '\n\n' + wrapped

	def generate(self, cwd: Path) -> GeneratorResult:
		"""Generate the agent file."""
		content = self.render()
		path = self.target_path(cwd)

		if path.exists() and self._is_managed(path):
			path.write_text(
				f'{MANAGED_MARKER}\n{content}',
				encoding='utf-8',
			)
			return GeneratorResult(
				agent=self._agent_name(),
				path=path,
				mode='updated',
				managed=True,
			)

		if path.exists():
			new_content = self._update_section(path, content)
			path.write_text(new_content, encoding='utf-8')
			return GeneratorResult(
				agent=self._agent_name(),
				path=path,
				mode='updated',
				managed=False,
			)

		path.parent.mkdir(parents=True, exist_ok=True)
		path.write_text(f'{MANAGED_MARKER}\n{content}', encoding='utf-8')
		return GeneratorResult(
			agent=self._agent_name(),
			path=path,
			mode='created',
			managed=True,
		)

	def _agent_name(self) -> str:
		return self.__class__.__name__.replace('FileGenerator', '').lower()


class CodexFileGenerator(AgentFileGenerator):
	"""Generates AGENTS.md for Codex CLI."""

	def render(self) -> str:
		return f"""# {self.project.name} — Agent Instructions

## imbalance KB

At session start: call `get_context` with task description.
After each decision: call `save_fact` immediately.
At session end: call `flush_session`.
Token budget: 2000.

## MCP Server

Server running at http://localhost:4731/mcp/sse
Project: {self.project.name}
"""

	def target_path(self, cwd: Path) -> Path:
		return cwd / 'AGENTS.md'


class ClaudeFileGenerator(AgentFileGenerator):
	"""Generates CLAUDE.md (symlink to AGENTS.md)."""

	def render(self) -> str:
		return f"""# {self.project.name} — Claude Code Instructions

## imbalance KB

Session start: /imbalance-load
Decisions: save_fact() immediately
Session end: /imbalance-flush
Context budget: 2000 tokens

## Extra hooks

Every 20 messages: call `report_context_usage`.
Before /compact: call `save_compaction_summary`.
"""

	def target_path(self, cwd: Path) -> Path:
		return cwd / 'CLAUDE.md'

	def generate(self, cwd: Path) -> GeneratorResult:
		agents_md = cwd / 'AGENTS.md'
		claude_md = self.target_path(cwd)

		if agents_md.exists() and not claude_md.exists():
			try:
				claude_md.symlink_to(agents_md)
				return GeneratorResult(
					agent='claude',
					path=claude_md,
					mode='linked',
					managed=True,
				)
			except OSError:
				pass

		return super().generate(cwd)


class GeminiFileGenerator(AgentFileGenerator):
	"""Generates GEMINI.md (symlink to AGENTS.md)."""

	def render(self) -> str:
		return f"""# {self.project.name} — Gemini CLI Instructions

## imbalance KB

At session start: call `get_context` with task description.
After each decision: call `save_fact` immediately.
At session end: call `flush_session`.
Token budget: 2000.
"""

	def target_path(self, cwd: Path) -> Path:
		return cwd / 'GEMINI.md'

	def generate(self, cwd: Path) -> GeneratorResult:
		agents_md = cwd / 'AGENTS.md'
		gemini_md = self.target_path(cwd)

		if agents_md.exists() and not gemini_md.exists():
			try:
				gemini_md.symlink_to(agents_md)
				return GeneratorResult(
					agent='gemini',
					path=gemini_md,
					mode='linked',
					managed=True,
				)
			except OSError:
				pass

		return super().generate(cwd)


class CursorFileGenerator(AgentFileGenerator):
	"""Generates .cursor/rules/imbalance.mdc for Cursor."""

	def render(self) -> str:
		return f"""---
description: imbalance knowledge base integration
alwaysApply: true
---

## imbalance KB

At session start: call `get_context` with current task.
After each significant decision: `save_fact`.
At session end: `flush_session`.

MCP server: running at http://localhost:4731/mcp/sse
Project: {self.project.name}
"""

	def target_path(self, cwd: Path) -> Path:
		return cwd / '.cursor' / 'rules' / 'imbalance.mdc'


class WindsurfFileGenerator(AgentFileGenerator):
	"""Generates .windsurfrules section for Windsurf."""

	def render(self) -> str:
		return """## imbalance KB

At session start: call `get_context` with task description.
After each decision: call `save_fact` immediately.
At session end: call `flush_session`.
Token budget: 2000.
MCP server: http://localhost:4731/mcp/sse
"""

	def target_path(self, cwd: Path) -> Path:
		return cwd / '.windsurfrules'


class CopilotFileGenerator(AgentFileGenerator):
	"""Generates .github/copilot-instructions.md section for GitHub Copilot."""

	def render(self) -> str:
		return """## imbalance KB

At session start: call `get_context` with task description.
After each decision: call `save_fact` immediately.
At session end: call `flush_session`.
Token budget: 2000.
"""

	def target_path(self, cwd: Path) -> Path:
		return cwd / '.github' / 'copilot-instructions.md'


TEMPLATES: dict[str, type[AgentFileGenerator]] = {
	'codex': CodexFileGenerator,
	'claude': ClaudeFileGenerator,
	'gemini': GeminiFileGenerator,
	'cursor': CursorFileGenerator,
	'windsurf': WindsurfFileGenerator,
	'copilot': CopilotFileGenerator,
}


class AgentFileGeneratorManager:
	"""Manages generation of all agent files."""

	def generate(
		self,
		agent: str | None,
		project: Project,
		cwd: Path,
		force: bool = False,
	) -> list[GeneratorResult]:
		"""Generate agent files. If agent is None, generate for all detected agents."""
		results: list[GeneratorResult] = []

		if agent:
			if agent not in TEMPLATES:
				raise ValueError(f'Unknown agent: {agent}. Available: {", ".join(TEMPLATES.keys())}')
			gen = TEMPLATES[agent](project)
			results.append(gen.generate(cwd))
		else:
			installed = detect_installed_agents()
			for name in installed:
				if name in TEMPLATES:
					gen = TEMPLATES[name](project)
					results.append(gen.generate(cwd))

		return results
