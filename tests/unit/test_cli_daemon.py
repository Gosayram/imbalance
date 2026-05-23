from typer.testing import CliRunner

from imbalance.cli.app import app

runner = CliRunner()


def test_daemon_start_command_shows_help() -> None:
	result = runner.invoke(app, ['daemon', '--help'])
	assert result.exit_code == 0
	assert 'Daemon commands' in result.output