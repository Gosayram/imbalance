import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from imbalance.server import ImbalanceDaemon


@pytest.mark.asyncio
async def test_daemon_init():
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	assert daemon.project.name == "test"
	assert daemon._accepting is True


@pytest.mark.asyncio
async def test_daemon_startup_error(tmp_path):
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=tmp_path, config_path=tmp_path / "test.toml", config=config, data_dir=tmp_path)
	daemon = ImbalanceDaemon(project)
	with patch("imbalance.server.open_db", side_effect=Exception("db error")):
		with pytest.raises(Exception):
			await daemon.startup()


@pytest.mark.asyncio
async def test_daemon_shutdown():
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	await daemon.shutdown()
	assert daemon._shutting_down is True
	assert daemon._accepting is False


@pytest.mark.asyncio
async def test_daemon_shutdown_idempotent():
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	await daemon.shutdown()
	await daemon.shutdown()
	assert daemon._shutting_down is True


@pytest.mark.asyncio
async def test_daemon_shutdown_with_in_flight():
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	daemon._in_flight.add(asyncio.create_task(asyncio.sleep(0.01)))
	await daemon.shutdown()
	assert daemon._shutting_down is True
