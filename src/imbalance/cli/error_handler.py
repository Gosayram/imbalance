from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from typing import Any

import typer

logger = logging.getLogger(__name__)


class CLIError(Exception):
	"""CLI error with exit code."""

	def __init__(self, message: str, exit_code: int = 1) -> None:
		self.message = message
		self.exit_code = exit_code
		super().__init__(message)


def handle_cli_errors(func: Callable[..., Any]) -> Callable[..., Any]:
	"""Decorator to handle CLI errors gracefully.

	Args:
		func: CLI function to wrap

	Returns:
		Wrapped function with error handling
	"""

	@functools.wraps(func)
	def wrapper(*args: Any, **kwargs: Any) -> Any:
		try:
			return func(*args, **kwargs)
		except CLIError as e:
			typer.echo(f'Error: {e.message}', err=True)
			raise typer.Exit(code=e.exit_code) from None
		except FileNotFoundError as e:
			typer.echo(f'File not found: {e}', err=True)
			raise typer.Exit(code=1) from None
		except PermissionError as e:
			typer.echo(f'Permission denied: {e}', err=True)
			raise typer.Exit(code=1) from None
		except KeyboardInterrupt:
			typer.echo('\nInterrupted', err=True)
			raise typer.Exit(code=130) from None
		except Exception as e:
			logger.exception('Unexpected error')
			typer.echo(f'Unexpected error: {e}', err=True)
			raise typer.Exit(code=1) from None

	return wrapper


def handle_async_cli_errors(func: Callable[..., Any]) -> Callable[..., Any]:
	"""Decorator to handle async CLI errors gracefully.

	Args:
		func: Async CLI function to wrap

	Returns:
		Wrapped function with error handling
	"""

	@functools.wraps(func)
	async def wrapper(*args: Any, **kwargs: Any) -> Any:
		try:
			return await func(*args, **kwargs)
		except CLIError as e:
			typer.echo(f'Error: {e.message}', err=True)
			raise typer.Exit(code=e.exit_code) from None
		except FileNotFoundError as e:
			typer.echo(f'File not found: {e}', err=True)
			raise typer.Exit(code=1) from None
		except PermissionError as e:
			typer.echo(f'Permission denied: {e}', err=True)
			raise typer.Exit(code=1) from None
		except KeyboardInterrupt:
			typer.echo('\nInterrupted', err=True)
			raise typer.Exit(code=130) from None
		except Exception as e:
			logger.exception('Unexpected error')
			typer.echo(f'Unexpected error: {e}', err=True)
			raise typer.Exit(code=1) from None

	return wrapper


def confirm_action(message: str, default: bool = False) -> bool:
	"""Confirm action with user.

	Args:
		message: Confirmation message
		default: Default value if user just presses Enter

	Returns:
		True if confirmed
	"""
	return typer.confirm(message, default=default)
