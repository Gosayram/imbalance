import pytest
from unittest.mock import patch, MagicMock
from imbalance.core.git_integration import git_commit_after_flush


def test_git_commit_disabled():
	with patch.dict('os.environ', {}, clear=True):
		result = git_commit_after_flush("/tmp", "test message")
		assert result is False


def test_git_commit_not_found():
	with patch.dict('os.environ', {'IMBALANCE_GIT_COMMIT': '1'}):
		with patch('imbalance.core.git_integration.subprocess.run') as mock_run:
			mock_run.side_effect = FileNotFoundError()
			result = git_commit_after_flush("/tmp", "test message")
			assert result is False


def test_git_commit_success():
	with patch.dict('os.environ', {'IMBALANCE_GIT_COMMIT': '1'}):
		with patch('imbalance.core.git_integration.subprocess.run') as mock_run:
			mock_run.return_value = MagicMock()
			result = git_commit_after_flush("/tmp", "test message")
			assert result is True
