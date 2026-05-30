from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any


class JSONFormatter(logging.Formatter):
	"""JSON log formatter for structured logging."""

	def format(self, record: logging.LogRecord) -> str:
		log_data: dict[str, Any] = {
			'timestamp': datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
			'level': record.levelname,
			'logger': record.name,
			'message': record.getMessage(),
		}

		if record.exc_info and record.exc_info[0] is not None:
			log_data['exception'] = self.formatException(record.exc_info)

		if hasattr(record, 'extra_data'):
			log_data.update(record.extra_data)

		return json.dumps(log_data, ensure_ascii=False)


def setup_logging(
	level: str = 'INFO',
	json_format: bool = False,
	stream: Any = None,
) -> None:
	"""Setup logging configuration.

	Args:
		level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
		json_format: Use JSON format for structured logging
		stream: Output stream (default: stderr)
	"""
	root_logger = logging.getLogger()
	root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

	# Remove existing handlers
	for handler in root_logger.handlers[:]:
		root_logger.removeHandler(handler)

	# Create handler
	handler = logging.StreamHandler(stream or sys.stderr)

	if json_format:
		handler.setFormatter(JSONFormatter())
	else:
		handler.setFormatter(logging.Formatter(
			'%(asctime)s %(levelname)s [%(name)s] %(message)s',
			datefmt='%Y-%m-%dT%H:%M:%S',
		))

	root_logger.addHandler(handler)


def get_logger(name: str, **extra: Any) -> logging.LoggerAdapter:
	"""Get logger with extra context fields.

	Args:
		name: Logger name
		**extra: Extra fields to include in log messages

	Returns:
		LoggerAdapter with extra context
	"""
	logger = logging.getLogger(name)
	return logging.LoggerAdapter(logger, {'extra_data': extra})
