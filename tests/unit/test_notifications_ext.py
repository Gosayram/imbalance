import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from imbalance.core.notifications_ext import (
	NotificationConfig,
	NotificationService,
	get_notification_service,
	set_notification_service,
)


def test_notification_config_defaults():
	config = NotificationConfig()
	assert config.slack_webhook_url is None
	assert config.discord_webhook_url is None
	assert config.enabled is True


def test_notification_config_custom():
	config = NotificationConfig(
		slack_webhook_url='https://hooks.slack.com/test',
		discord_webhook_url='https://discord.com/api/webhooks/test',
		enabled=False,
	)
	assert config.slack_webhook_url == 'https://hooks.slack.com/test'
	assert config.discord_webhook_url == 'https://discord.com/api/webhooks/test'
	assert config.enabled is False


@pytest.mark.asyncio
async def test_send_slack_no_webhook():
	service = NotificationService(NotificationConfig())
	result = await service.send_slack('test message')
	assert result is False


@pytest.mark.asyncio
async def test_send_discord_no_webhook():
	service = NotificationService(NotificationConfig())
	result = await service.send_discord('test message')
	assert result is False


@pytest.mark.asyncio
async def test_send_no_channels():
	service = NotificationService(NotificationConfig())
	results = await service.send('test message')
	assert results == {}


def test_get_notification_service_singleton():
	service1 = get_notification_service()
	service2 = get_notification_service()
	assert service1 is service2


def test_set_notification_service():
	custom = NotificationService(NotificationConfig(enabled=False))
	set_notification_service(custom)
	assert get_notification_service() is custom
