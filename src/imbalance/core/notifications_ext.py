from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NotificationConfig:
	"""Notification configuration."""
	slack_webhook_url: str | None = None
	discord_webhook_url: str | None = None
	enabled: bool = True


class NotificationService:
	"""Service for sending notifications to Slack/Discord."""

	def __init__(self, config: NotificationConfig | None = None) -> None:
		self.config = config or NotificationConfig(
			slack_webhook_url=os.environ.get('SLACK_WEBHOOK_URL'),
			discord_webhook_url=os.environ.get('DISCORD_WEBHOOK_URL'),
		)

	async def send_slack(self, message: str, channel: str | None = None) -> bool:
		"""Send notification to Slack.

		Args:
			message: Message to send
			channel: Slack channel (optional)

		Returns:
			True if sent successfully
		"""
		if not self.config.slack_webhook_url:
			logger.debug('Slack webhook not configured')
			return False

		try:
			import aiohttp

			payload: dict[str, Any] = {'text': message}
			if channel:
				payload['channel'] = channel

			async with aiohttp.ClientSession() as session, session.post(
				self.config.slack_webhook_url,
				json=payload,
			) as response:
				if response.status == 200:
					logger.info('Slack notification sent')
					return True
				else:
					logger.warning(f'Slack notification failed: {response.status}')
					return False
		except Exception as e:
			logger.error(f'Slack notification error: {e}')
			return False

	async def send_discord(self, message: str) -> bool:
		"""Send notification to Discord.

		Args:
			message: Message to send

		Returns:
			True if sent successfully
		"""
		if not self.config.discord_webhook_url:
			logger.debug('Discord webhook not configured')
			return False

		try:
			import aiohttp

			payload = {'content': message}

			async with aiohttp.ClientSession() as session, session.post(
				self.config.discord_webhook_url,
				json=payload,
			) as response:
				if response.status in (200, 204):
					logger.info('Discord notification sent')
					return True
				else:
					logger.warning(f'Discord notification failed: {response.status}')
					return False
		except Exception as e:
			logger.error(f'Discord notification error: {e}')
			return False

	async def send(self, message: str, channel: str | None = None) -> dict[str, bool]:
		"""Send notification to all configured channels.

		Args:
			message: Message to send
			channel: Slack channel (optional)

		Returns:
			Dict of channel -> success
		"""
		results: dict[str, bool] = {}

		if self.config.slack_webhook_url:
			results['slack'] = await self.send_slack(message, channel)

		if self.config.discord_webhook_url:
			results['discord'] = await self.send_discord(message)

		return results


# Global notification service
_global_service: NotificationService | None = None


def get_notification_service() -> NotificationService:
	"""Get global notification service."""
	global _global_service
	if _global_service is None:
		_global_service = NotificationService()
	return _global_service


def set_notification_service(service: NotificationService) -> None:
	"""Set global notification service."""
	global _global_service
	_global_service = service
