import pytest
from imbalance.graph._constants import SKIP_DIRS, SOURCE_EXTS, _EXT_TO_LANG


def test_skip_dirs_is_frozenset():
	assert isinstance(SKIP_DIRS, frozenset)


def test_skip_dirs_contains_common():
	assert '.git' in SKIP_DIRS
	assert '__pycache__' in SKIP_DIRS
	assert '.venv' in SKIP_DIRS


def test_source_exts_is_frozenset():
	assert isinstance(SOURCE_EXTS, frozenset)


def test_source_exts_contains_common():
	assert '.py' in SOURCE_EXTS
	assert '.js' in SOURCE_EXTS
	assert '.go' in SOURCE_EXTS


def test_ext_to_lang():
	assert _EXT_TO_LANG['.py'] == 'python'
	assert _EXT_TO_LANG['.ts'] == 'typescript'
	assert _EXT_TO_LANG['.go'] == 'go'
