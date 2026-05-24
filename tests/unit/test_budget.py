from __future__ import annotations

from imbalance.core.budget import SessionBudgetMonitor


def test_ok_below_warn_threshold():
	monitor = SessionBudgetMonitor()
	action = monitor.check(used_tokens=100, total_tokens=1000)
	assert action.action == 'ok'
	assert action.message == ''


def test_warn_at_70_percent():
	monitor = SessionBudgetMonitor()
	action = monitor.check(used_tokens=700, total_tokens=1000)
	assert action.action == 'warn'
	assert '70%' in action.message


def test_critical_at_85_percent():
	monitor = SessionBudgetMonitor()
	action = monitor.check(used_tokens=850, total_tokens=1000)
	assert action.action == 'save_critical_now'
	assert '85%' in action.message


def test_emergency_at_95_percent():
	monitor = SessionBudgetMonitor()
	action = monitor.check(used_tokens=950, total_tokens=1000)
	assert action.action == 'emergency_flush'
	assert '95%' in action.message


def test_zero_total_returns_ok():
	monitor = SessionBudgetMonitor()
	action = monitor.check(used_tokens=0, total_tokens=0)
	assert action.action == 'ok'


def test_custom_thresholds():
	monitor = SessionBudgetMonitor(warn_ratio=0.5, critical_ratio=0.7, emergency_ratio=0.9)
	action = monitor.check(used_tokens=500, total_tokens=1000)
	assert action.action == 'warn'
