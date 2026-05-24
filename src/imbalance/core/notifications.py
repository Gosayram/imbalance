from __future__ import annotations

import logging
import platform
import subprocess

logger = logging.getLogger(__name__)


def send_system_notification(title: str, message: str) -> bool:
	system = platform.system()
	try:
		if system == 'Darwin':
			escaped_title = title.replace('"', '\\"').replace("'", "\\'")
			escaped_msg = message.replace('"', '\\"').replace("'", "\\'")
			script = f'display notification "{escaped_msg}" with title "{escaped_title}"'
			subprocess.run(['osascript', '-e', script], check=True, timeout=5)
			return True
		elif system == 'Linux':
			subprocess.run(
				['notify-send', title, message], check=True, timeout=5
			)
			return True
		else:
			logger.debug(f'Notifications not supported on {system}')
			return False
	except (subprocess.SubprocessError, FileNotFoundError, OSError) as e:
		logger.warning(f'Notification failed: {e}')
		return False


def check_kb_health(
	queue_depth: int,
	last_flush_age_days: float,
	circuit_breaker_open: bool,
	queue_threshold: int = 5,
	stale_days: float = 14.0,
) -> list[str]:
	alerts: list[str] = []
	if queue_depth > queue_threshold:
		alerts.append(f'Flush queue has {queue_depth} pending items (threshold: {queue_threshold})')
	if last_flush_age_days > stale_days:
		alerts.append(f'KB not updated for {last_flush_age_days:.0f} days (threshold: {stale_days:.0f})')
	if circuit_breaker_open:
		alerts.append('Circuit breaker is open — provider unavailable')
	return alerts


def notify_alerts(alerts: list[str]) -> int:
	if not alerts:
		return 0
	message = '; '.join(alerts)
	send_system_notification('imbalance', message)
	return len(alerts)
