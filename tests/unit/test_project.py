import pytest
from pathlib import Path
from imbalance.core.project import InheritConfig, NotificationConfig, ProjectConfig, Project, default_data_dir


def test_inherit_config_defaults():
	config = InheritConfig(kb_name="parent")
	assert config.kb_name == "parent"
	assert config.weight == 0.5


def test_notification_config_defaults():
	config = NotificationConfig()
	assert config.enabled is True
	assert config.queue_size_threshold == 5


def test_project_config_defaults():
	config = ProjectConfig(name="test", version="1")
	assert config.name == "test"
	assert config.budget_tokens == 2000
	assert config.notifications.enabled is True


def test_default_data_dir():
	result = default_data_dir()
	assert isinstance(result, Path)
