import json
import logging
import pytest
from io import StringIO
from imbalance.core.logging import JSONFormatter, setup_logging, get_logger


def test_json_formatter():
	formatter = JSONFormatter()
	record = logging.LogRecord(
		name='test',
		level=logging.INFO,
		pathname='test.py',
		lineno=1,
		msg='test message',
		args=None,
		exc_info=None,
	)
	result = formatter.format(record)
	data = json.loads(result)

	assert data['level'] == 'INFO'
	assert data['logger'] == 'test'
	assert data['message'] == 'test message'
	assert 'timestamp' in data


def test_json_formatter_with_exception():
	formatter = JSONFormatter()
	try:
		raise ValueError('test error')
	except ValueError:
		import sys
		record = logging.LogRecord(
			name='test',
			level=logging.ERROR,
			pathname='test.py',
			lineno=1,
			msg='error occurred',
			args=None,
			exc_info=sys.exc_info(),
		)
		result = formatter.format(record)
		data = json.loads(result)

		assert data['level'] == 'ERROR'
		assert 'exception' in data
		assert 'ValueError: test error' in data['exception']


def test_setup_logging_default():
	stream = StringIO()
	setup_logging(level='INFO', json_format=False, stream=stream)

	logger = logging.getLogger('test')
	logger.info('test message')

	output = stream.getvalue()
	assert 'test message' in output


def test_setup_logging_json():
	stream = StringIO()
	setup_logging(level='INFO', json_format=True, stream=stream)

	logger = logging.getLogger('test')
	logger.info('test message')

	output = stream.getvalue()
	data = json.loads(output)
	assert data['message'] == 'test message'
	assert data['level'] == 'INFO'


def test_get_logger():
	logger = get_logger('test', user_id='123', request_id='abc')
	assert isinstance(logger, logging.LoggerAdapter)
	assert logger.extra == {'extra_data': {'user_id': '123', 'request_id': 'abc'}}
