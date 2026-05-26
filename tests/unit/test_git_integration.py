import pytest
import tempfile
from unittest.mock import patch, MagicMock
from imbalance.core.git_integration import git_commit_after_flush
import subprocess


def test_git_commit_disabled(tmp_path):
	with patch.dict('os.environ', {}, clear=True):
		result = git_commit_after_flush(str(tmp_path), "test message")
		assert result is False


def test_git_commit_not_found(tmp_path):
	with patch.dict('os.environ', {'IMBALANCE_GIT_COMMIT': '1'}):
		with patch('imbalance.core.git_integration.subprocess.run') as mock_run:
			mock_run.side_effect = FileNotFoundError()
			result = git_commit_after_flush(str(tmp_path), "test message")
			assert result is False


def test_git_commit_success(tmp_path):
	with patch.dict('os.environ', {'IMBALANCE_GIT_COMMIT': '1'}):
		with patch('imbalance.core.git_integration.subprocess.run') as mock_run:
			mock_run.return_value = MagicMock()
			result = git_commit_after_flush(str(tmp_path), "test message")
			assert result is True


def test_git_commit_error(tmp_path):
	with patch.dict('os.environ', {'IMBALANCE_GIT_COMMIT': '1'}):
		with patch('imbalance.core.git_integration.subprocess.run') as mock_run:
			mock_run.side_effect = subprocess.CalledProcessError(1, 'git', stderr=b'fatal: not a git repo')
			result = git_commit_after_flush(str(tmp_path), "test message")
			assert result is False
