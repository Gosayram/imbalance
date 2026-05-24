from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

MARKERS = {
	'DECISION': 'decisions',
	'PATTERN': 'patterns',
	'TODO': 'issues',
	'FIXME': 'issues',
	'NOTE': 'notes',
}

_MARKER_RE = re.compile(
	r'#\s*IMBALANCE:(DECISION|PATTERN|TODO|FIXME|NOTE):\s*(.*)',
	re.IGNORECASE,
)

_EXTS = {'.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.java', '.kt', '.rb', '.sh'}


@dataclass(frozen=True)
class ScanHit:
	file: Path
	line: int
	marker_type: str
	section: str
	content: str
	context_lines: list[str]


def scan_directory(
	root: Path,
	exts: set[str] | None = None,
) -> list[ScanHit]:
	exts = exts or _EXTS
	hits: list[ScanHit] = []

	for path in sorted(root.rglob('*')):
		if not path.is_file():
			continue
		if path.suffix not in exts:
			continue
		if any(part.startswith('.') for part in path.relative_to(root).parts):
			continue

		lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
		for i, line in enumerate(lines):
			m = _MARKER_RE.match(line.strip())
			if not m:
				continue
			marker_type = m.group(1).upper()
			section = MARKERS.get(marker_type, 'notes')
			content = m.group(2).strip()
			ctx_start = max(0, i - 1)
			ctx_end = min(len(lines), i + 3)
			hits.append(
				ScanHit(
					file=path,
					line=i + 1,
					marker_type=marker_type,
					section=section,
					content=content,
					context_lines=lines[ctx_start:ctx_end],
				)
			)

	return hits
