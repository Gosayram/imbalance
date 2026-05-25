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


def test_budget_monitor_zero_total():
	monitor = SessionBudgetMonitor()
	action = monitor.check(100, 0)
	assert action.action == "ok"


def test_budget_monitor_negative_used():
	monitor = SessionBudgetMonitor()
	action = monitor.check(-10, 1000)
	assert action.action == "ok"


def test_budget_monitor_exact_warn():
	monitor = SessionBudgetMonitor(warn_ratio=0.7)
	action = monitor.check(700, 1000)
	assert action.action == "warn"


def test_budget_monitor_exact_critical():
	monitor = SessionBudgetMonitor(critical_ratio=0.8)
	action = monitor.check(800, 1000)
	assert action.action == "save_critical_now"


def test_budget_monitor_exact_emergency():
	monitor = SessionBudgetMonitor(emergency_ratio=0.9)
	action = monitor.check(900, 1000)
	assert action.action == "emergency_flush"


def test_budget_monitor_custom_ratios():
	monitor = SessionBudgetMonitor(warn_ratio=0.3, critical_ratio=0.5, emergency_ratio=0.8)
	action1 = monitor.check(350, 1000)
	assert action1.action == "warn"
	action2 = monitor.check(600, 1000)
	assert action2.action == "save_critical_now"
	action3 = monitor.check(850, 1000)
	assert action3.action == "emergency_flush"
