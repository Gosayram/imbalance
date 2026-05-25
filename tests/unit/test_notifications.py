import pytest
from imbalance.core.notifications import check_kb_health, notify_alerts


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
