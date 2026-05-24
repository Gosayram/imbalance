from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from imbalance.cli.app import app

runner = CliRunner()


def test_daemon_start_command_shows_help() -> None:
	result = runner.invoke(app, ['daemon', '--help'])
	assert result.exit_code == 0
	assert 'Daemon commands' in result.output


def test_daemon_stop_no_pid_file(tmp_path: Path) -> None:
	fake_pid = tmp_path / 'daemon.pid'
	with patch('imbalance.server.PID_FILE', fake_pid):
		result = runner.invoke(app, ['daemon', 'stop'])
	assert result.exit_code == 1
	assert 'No daemon PID file found' in result.output


def test_project_info_command() -> None:
	result = runner.invoke(app, ['project', 'info'])
	assert result.exit_code == 0
	assert 'name:' in result.output


def test_queue_status_command() -> None:
	result = runner.invoke(app, ['queue', 'status'])
	assert result.exit_code == 0
	assert 'queued:' in result.output


def test_session_list_command() -> None:
	result = runner.invoke(app, ['session', 'list'])
	assert result.exit_code == 0
