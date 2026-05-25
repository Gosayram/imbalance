import pytest
from pathlib import Path
from imbalance.core.scanner import ScanHit, scan_directory, MARKERS, _MARKER_RE


def test_markers():
	assert 'DECISION' in MARKERS
	assert MARKERS['DECISION'] == 'decisions'


def test_marker_re():
	m = _MARKER_RE.match('# IMBALANCE:DECISION: test content')
	assert m is not None
	assert m.group(1) == 'DECISION'
	assert m.group(2) == 'test content'


def test_marker_re_case_insensitive():
	m = _MARKER_RE.match('# imbalance:todo: test')
	assert m is not None
	assert m.group(1).upper() == 'TODO'


def test_scan_hit():
	hit = ScanHit(
		file=Path("test.py"),
		line=10,
		marker_type="DECISION",
		section="decisions",
		content="test",
		context_lines=["line1", "line2"],
	)
	assert hit.file.name == "test.py"


@pytest.mark.asyncio
async def test_scan_directory_empty(tmp_path):
	hits = scan_directory(tmp_path)
	assert hits == []