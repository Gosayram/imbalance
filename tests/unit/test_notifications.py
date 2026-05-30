import pytest
from unittest.mock import patch
from imbalance.core.notifications import check_kb_health, notify_alerts, send_system_notification


def test_check_kb_health_no_alerts():
	alerts = check_kb_health(
		queue_depth=0,
		last_flush_age_days=0,
		circuit_breaker_open=False,
		queue_threshold=5,
		stale_days=14,
	)
	assert alerts == []


def test_check_kb_health_queue_alert():
	alerts = check_kb_health(
		queue_depth=10,
		last_flush_age_days=0,
		circuit_breaker_open=False,
		queue_threshold=5,
		stale_days=14,
	)
	assert len(alerts) == 1


def test_check_kb_health_stale_alert():
	alerts = check_kb_health(
		queue_depth=0,
		last_flush_age_days=20,
		circuit_breaker_open=False,
		queue_threshold=5,
		stale_days=14,
	)
	assert len(alerts) == 1


def test_notify_alerts():
	alerts = ["warning: test alert"]
	result = notify_alerts(alerts)
	assert result == 1


def test_check_kb_health_circuit_breaker():
	alerts = check_kb_health(
		queue_depth=0,
		last_flush_age_days=0,
		circuit_breaker_open=True,
		queue_threshold=5,
		stale_days=14,
	)
	assert len(alerts) == 1


def test_check_kb_health_multiple_alerts():
	alerts = check_kb_health(
		queue_depth=10,
		last_flush_age_days=20,
		circuit_breaker_open=False,
		queue_threshold=5,
		stale_days=14,
	)
	assert len(alerts) == 2


def test_notify_alerts_empty():
	result = notify_alerts([])
	assert result == 0


def test_send_notification_linux():
	with patch("imbalance.core.notifications.platform.system", return_value="Linux"):
		with patch("imbalance.core.notifications.subprocess.run") as mock_run:
			result = send_system_notification("test", "message")
			assert result == True
			mock_run.assert_called()


def test_send_notification_unsupported():
	with patch("imbalance.core.notifications.platform.system", return_value="Windows"):
		result = send_system_notification("test", "message")
		assert result == False


def test_send_notification_linux_error():
	with patch("imbalance.core.notifications.platform.system", return_value="Linux"):
		with patch("imbalance.core.notifications.subprocess.run", side_effect=FileNotFoundError()):
			result = send_system_notification("test", "message")
			assert result == False
