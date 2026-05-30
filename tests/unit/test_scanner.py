import pytest
from pathlib import Path
from imbalance.core.scanner import ScanHit, scan_directory, MARKERS, _MARKER_RE, _EXTS


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


def test_exts():
	assert '.py' in _EXTS
	assert '.js' in _EXTS


def test_scan_directory_empty(tmp_path):
	hits = scan_directory(tmp_path)
	assert hits == []


def test_scan_directory_with_file(tmp_path):
	test_file = tmp_path / "test.py"
	test_file.write_text("# IMBALANCE:DECISION: important decision\n")
	hits = scan_directory(tmp_path)
	assert len(hits) == 1
	assert hits[0].marker_type == 'DECISION'


def test_scan_directory_with_multiple_markers(tmp_path):
	test_file = tmp_path / "test.py"
	test_file.write_text("# IMBALANCE:TODO: task 1\n# IMBALANCE:FIXME: fix this\n")
	hits = scan_directory(tmp_path)
	assert len(hits) == 2


def test_scan_directory_skips_hidden(tmp_path):
	hidden_dir = tmp_path / ".git"
	hidden_dir.mkdir()
	test_file = hidden_dir / "test.py"
	test_file.write_text("# IMBALANCE:DECISION: test\n")
	hits = scan_directory(tmp_path)
	assert len(hits) == 0


def test_scan_directory_all_marker_types(tmp_path):
	test_file = tmp_path / "test.py"
	test_file.write_text(
		"# IMBALANCE:DECISION: decision\n"
		"# IMBALANCE:PATTERN: pattern\n"
		"# IMBALANCE:TODO: todo\n"
		"# IMBALANCE:FIXME: fixme\n"
		"# IMBALANCE:NOTE: note\n"
	)
	hits = scan_directory(tmp_path)
	assert len(hits) == 5
	assert hits[0].section == 'decisions'
	assert hits[1].section == 'patterns'
	assert hits[2].section == 'issues'
	assert hits[3].section == 'issues'
	assert hits[4].section == 'notes'


def test_scan_directory_custom_exts(tmp_path):
	test_file = tmp_path / "test.rb"
	test_file.write_text("# IMBALANCE:DECISION: ruby decision\n")
	hits = scan_directory(tmp_path, exts={'.rb'})
	assert len(hits) == 1


def test_scan_directory_skips_missing_exts(tmp_path):
	test_file = tmp_path / "test.txt"
	test_file.write_text("# IMBALANCE:DECISION: should skip\n")
	hits = scan_directory(tmp_path)
	assert len(hits) == 0