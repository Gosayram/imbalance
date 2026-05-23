from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ContextMode(StrEnum):
	OFF = 'off'
	READ_ONLY = 'read_only'
	WRITE_ONLY = 'write_only'
	READ_WRITE = 'read_write'


@dataclass(frozen=True)
class ContextChunk:
	slug: str
	section: str
	content: str
	score: float
	token_count: int
	confidence: float = 0.5


@dataclass(frozen=True)
class ContextPack:
	query: str
	budget_tokens: int
	precedence: list[str]
	summary: str | None
	evidence: list[ContextChunk]
	omitted: list[str] = field(default_factory=list)
	warnings: list[str] = field(default_factory=list)

	def render_markdown(self) -> str:
		parts = [
			'<context-pack>',
			f'<precedence>{" > ".join(self.precedence)}</precedence>',
		]
		if self.summary:
			parts.extend(['<memory-summary>', self.summary, '</memory-summary>'])
		for chunk in self.evidence:
			parts.extend(
				[
					f'<evidence slug="{chunk.slug}" section="{chunk.section}" '
					f'confidence="{chunk.confidence:.2f}">',
					chunk.content,
					'</evidence>',
				]
			)
		if self.warnings:
			parts.extend(['<warnings>', '\n'.join(self.warnings), '</warnings>'])
		parts.append('</context-pack>')
		return '\n'.join(parts)
