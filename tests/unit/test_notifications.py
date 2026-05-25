import pytest
from unittest.mock import patch, MagicMock
from imbalance.core.notifications import check_kb_health, notify_alerts, send_system_notification


def test_check_kb_health_healthy():
	alerts = check_kb_health(0, 0, False, queue_threshold=5, stale_days=14.0)
	assert alerts == []


def test_check_kb_health_queue_depth():
	alerts = check_kb_health(10, 0, False, queue_threshold=5)
	assert len(alerts) == 1
	assert 'queue' in alerts[0]


def test_check_kb_health_stale():
	alerts = check_kb_health(0, 20.0, False, stale_days=14.0)
	assert len(alerts) == 1
	assert 'not updated' in alerts[0]


def test_check_kb_health_circuit_breaker():
	alerts = check_kb_health(0, 0, True)
	assert len(alerts) == 1
	assert 'Circuit breaker' in alerts[0]


def test_notify_alerts_empty():
	result = notify_alerts([])
	assert result == 0


def test_notify_alerts_with_alerts():
	with patch('imbalance.core.notifications.send_system_notification') as mock_send:
		result = notify_alerts(['alert1', 'alert2'])
		assert result == 2
		mock_send.assert_called()


def test_send_system_notification_unsupported():
	with patch('imbalance.core.notifications.platform.system', return_value='Windows'):
		result = send_system_notification("title", "message")
		assert result is False
