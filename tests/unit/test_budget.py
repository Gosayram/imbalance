import pytest
from imbalance.core.budget import BudgetAction, SessionBudgetMonitor


def test_budget_action_defaults():
	action = BudgetAction(action="test")
	assert action.action == "test"
	assert action.message == ""


def test_budget_action_with_message():
	action = BudgetAction(action="warn", message="test message")
	assert action.action == "warn"
	assert action.message == "test message"


def test_budget_monitor_ok():
	monitor = SessionBudgetMonitor()
	action = monitor.check(100, 1000)
	assert action.action == "ok"


def test_budget_monitor_warn():
	monitor = SessionBudgetMonitor(warn_ratio=0.5)
	action = monitor.check(600, 1000)
	assert action.action == "warn"


def test_budget_monitor_critical():
	monitor = SessionBudgetMonitor(critical_ratio=0.7)
	action = monitor.check(800, 1000)
	assert action.action == "save_critical_now"


def test_budget_monitor_emergency():
	monitor = SessionBudgetMonitor(emergency_ratio=0.9)
	action = monitor.check(950, 1000)
	assert action.action == "emergency_flush"
