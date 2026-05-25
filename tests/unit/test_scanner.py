import pytest
from pathlib import Path
from imbalance.core.scanner import scan_directory, ScanHit, _MARKER_RE, MARKERS


def test_marker_re_match():
	match = _MARKER_RE.match("# IMBALANCE:TODO: fix this")
	assert match is not None
	assert match.group(1) == "TODO"
	assert match.group(2) == "fix this"


def test_markers_content():
	assert MARKERS["DECISION"] == "decisions"
	assert MARKERS["TODO"] == "issues"


def test_scan_directory_no_files(tmp_path):
	result = scan_directory(tmp_path)
	assert result == []


def test_scan_directory_with_markers(tmp_path):
	test_file = tmp_path / "test.py"
	test_file.write_text("# IMBALANCE:TODO: implement this\n# IMBALANCE:DECISION: use postgres\n")
	result = scan_directory(tmp_path)
	assert len(result) == 2
	assert result[0].marker_type == "TODO"
	assert result[1].marker_type == "DECISION"


def test_scan_directory_skip_hidden(tmp_path):
	hidden_dir = tmp_path / ".hidden"
	hidden_dir.mkdir()
	hidden_file = hidden_dir / "test.py"
	hidden_file.write_text("# IMBALANCE:TODO: hidden\n")
	result = scan_directory(tmp_path)
	assert len(result) == 0
