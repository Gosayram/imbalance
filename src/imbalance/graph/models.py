from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Symbol:
	name: str
	kind: str
	file_path: str
	line: int
	end_line: int
	signature: str
	language: str


@dataclass(frozen=True, slots=True)
class ParseResult:
	file_path: str
	symbols: tuple[Symbol, ...]
	error: str | None = None


@dataclass(frozen=True, slots=True)
class IndexStats:
	files: int
	symbols: int
	edges: int
	duration_ms: float
	peak_rss_mb: float


@dataclass(slots=True)
class WatcherState:
	pending_files: set[str]
	last_sync_at: float
	is_running: bool = False