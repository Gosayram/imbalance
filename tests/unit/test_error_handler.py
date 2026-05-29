import pytest
from unittest.mock import MagicMock, patch
import click.exceptions
from imbalance.cli.error_handler import (
	CLIError,
	handle_cli_errors,
	handle_async_cli_errors,
	confirm_action,
)


def test_cli_error():
	error = CLIError('test error', exit_code=2)
	assert error.message == 'test error'
	assert error.exit_code == 2
	assert str(error) == 'test error'


def test_cli_error_default_exit_code():
	error = CLIError('test error')
	assert error.exit_code == 1


def test_handle_cli_errors_success():
	@handle_cli_errors
	def func():
		return 'success'

	assert func() == 'success'


def test_handle_cli_errors_file_not_found():
	@handle_cli_errors
	def func():
		raise FileNotFoundError('file.txt')

	with pytest.raises(click.exceptions.Exit):
		func()


def test_handle_cli_errors_permission_error():
	@handle_cli_errors
	def func():
		raise PermissionError('denied')

	with pytest.raises(click.exceptions.Exit):
		func()


def test_handle_cli_errors_keyboard_interrupt():
	@handle_cli_errors
	def func():
		raise KeyboardInterrupt()

	with pytest.raises(click.exceptions.Exit):
		func()


def test_handle_cli_errors_generic_exception():
	@handle_cli_errors
	def func():
		raise RuntimeError('unexpected')

	with pytest.raises(click.exceptions.Exit):
		func()


@pytest.mark.asyncio
async def test_handle_async_cli_errors_success():
	@handle_async_cli_errors
	async def func():
		return 'success'

	result = await func()
	assert result == 'success'


@pytest.mark.asyncio
async def test_handle_async_cli_errors_file_not_found():
	@handle_async_cli_errors
	async def func():
		raise FileNotFoundError('file.txt')

	with pytest.raises(click.exceptions.Exit):
		await func()


@pytest.mark.asyncio
async def test_handle_async_cli_errors_generic_exception():
	@handle_async_cli_errors
	async def func():
		raise RuntimeError('unexpected')

	with pytest.raises(click.exceptions.Exit):
		await func()
