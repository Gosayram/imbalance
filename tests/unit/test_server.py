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


@pytest.mark.asyncio
async def test_daemon_startup_success(tmp_path):
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=tmp_path, config_path=tmp_path / "test.toml", config=config, data_dir=tmp_path)
	daemon = ImbalanceDaemon(project)
	mock_db = AsyncMock()
	with patch("imbalance.server.open_db", return_value=mock_db):
		with patch("imbalance.server.run_migrations"):
			with patch("imbalance.server.SessionManager") as mock_sm:
				mock_sm.return_value.recover_pending = AsyncMock(return_value=(0, 0))
				with patch("imbalance.server.ModelRouter"):
					with patch("imbalance.server.ImbalanceDaemon._process_flush_queue"):
						with patch("imbalance.server.ImbalanceDaemon._check_notifications"):
							await daemon.startup()


@pytest.mark.asyncio
async def test_process_flush_queue_no_db():
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	await daemon._process_flush_queue()


@pytest.mark.asyncio
async def test_process_flush_queue_no_router():
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	daemon.db = AsyncMock()
	daemon._router = None
	await daemon._process_flush_queue()


@pytest.mark.asyncio
async def test_check_notifications_no_db():
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	await daemon._check_notifications()


@pytest.mark.asyncio
async def test_handle_signal():
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	daemon._server = MagicMock()
	import signal
	await daemon._handle_signal(signal.SIGTERM)
	assert daemon._server.should_exit is True


@pytest.mark.asyncio
async def test_check_notifications_disabled():
	from imbalance.core.project import Project, ProjectConfig, NotificationConfig
	config = ProjectConfig(name="test", version="1", notifications=NotificationConfig(enabled=False))
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	daemon.db = AsyncMock()
	await daemon._check_notifications()


@pytest.mark.asyncio
async def test_shutdown_with_db():
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	daemon.db = AsyncMock()
	with patch("imbalance.server.checkpoint") as mock_checkpoint:
		await daemon.shutdown()
		mock_checkpoint.assert_called()


@pytest.mark.asyncio
async def test_shutdown_checkpoint_error():
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	daemon.db = AsyncMock()
	with patch("imbalance.server.checkpoint", side_effect=Exception("checkpoint error")):
		await daemon.shutdown()


@pytest.mark.asyncio
async def test_shutdown_with_in_flight_timeout():
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	daemon.db = AsyncMock()
	daemon._in_flight.add(asyncio.create_task(asyncio.sleep(10)))
	await daemon.shutdown()


@pytest.mark.asyncio
async def test_register_signal_handlers():
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	daemon.register_signal_handlers()


@pytest.mark.asyncio
async def test_handle_signal_no_server():
	from imbalance.core.project import Project, ProjectConfig
	import signal
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	daemon._server = None
	await daemon._handle_signal(signal.SIGTERM)


@pytest.mark.asyncio
async def test_pid_file_created():
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	mock_db = AsyncMock()
	with patch("imbalance.server.open_db", return_value=mock_db):
		with patch("imbalance.server.run_migrations"):
			with patch("imbalance.server.SessionManager") as mock_sm:
				mock_sm.return_value.recover_pending = AsyncMock(return_value=(0, 0))
				with patch("imbalance.server.ModelRouter"):
					with patch("imbalance.server.ImbalanceDaemon._process_flush_queue"):
						with patch("imbalance.server.ImbalanceDaemon._check_notifications"):
							await daemon.startup()
							assert daemon.db is mock_db


@pytest.mark.asyncio
async def test_daemon_startup_db_error_closes_db():
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	mock_db = AsyncMock()
	with patch("imbalance.server.open_db", return_value=mock_db):
		with patch("imbalance.server.run_migrations", side_effect=Exception("migration error")):
			with pytest.raises(Exception):
				await daemon.startup()


@pytest.mark.asyncio
async def test_process_flush_queue_with_items():
	from imbalance.core.project import Project, ProjectConfig
	from imbalance.core.queue import FlushQueue
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	daemon.db = AsyncMock()
	mock_router = AsyncMock()
	mock_router.complete = AsyncMock(return_value="summary delta")
	mock_router.apply_delta = AsyncMock()
	daemon._router = mock_router

	mock_item = MagicMock()
	mock_item.id = 1
	mock_item.session_id = "test-session"
	mock_item.payload = b'{"summary": "test", "decisions": [], "next_steps": []}'
	mock_item.attempts = 0

	with patch("imbalance.server.FlushQueue") as mock_queue_cls:
		mock_queue = AsyncMock()
		mock_queue.due = AsyncMock(return_value=[mock_item])
		mock_queue_cls.return_value = mock_queue
		with patch("imbalance.server.FlushPayload") as mock_payload:
			mock_payload.from_json = MagicMock(return_value=MagicMock())
			await daemon._process_flush_queue()


@pytest.mark.asyncio
async def test_process_flush_queue_success_with_session_manager():
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	daemon.db = AsyncMock()
	mock_router = AsyncMock()
	mock_router.complete = AsyncMock(return_value="delta")
	mock_router.apply_delta = AsyncMock()
	daemon._router = mock_router
	daemon.session_manager = AsyncMock()

	mock_item = MagicMock()
	mock_item.id = 1
	mock_item.session_id = "test-session"
	mock_item.payload = b'{"summary": "test", "decisions": [], "next_steps": []}'
	mock_item.attempts = 0

	with patch("imbalance.server.FlushQueue") as mock_queue_cls:
		mock_queue = AsyncMock()
		mock_queue.due = AsyncMock(return_value=[mock_item])
		mock_queue_cls.return_value = mock_queue
		with patch("imbalance.server.FlushPayload") as mock_payload:
			mock_payload.from_json = MagicMock(return_value=MagicMock())
			await daemon._process_flush_queue()


@pytest.mark.asyncio
async def test_check_notifications_with_alerts():
	from imbalance.core.project import Project, ProjectConfig, NotificationConfig
	config = ProjectConfig(name="test", version="1", notifications=NotificationConfig(enabled=True, queue_size_threshold=10, kb_stale_days=7))
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	mock_db = AsyncMock()
	mock_db.execute_fetchone = AsyncMock(side_effect=[
		{'cnt': 15},
		{'last': '2024-01-01T00:00:00Z'}
	])
	daemon.db = mock_db
	with patch("imbalance.core.notifications.check_kb_health", return_value=["dummy alert"]):
		with patch("imbalance.core.notifications.notify_alerts"):
			await daemon._check_notifications()


@pytest.mark.asyncio
async def test_daemon_startup_with_recovered_sessions():
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	mock_db = AsyncMock()
	with patch("imbalance.server.open_db", return_value=mock_db):
		with patch("imbalance.server.run_migrations"):
			with patch("imbalance.server.SessionManager") as mock_sm:
				mock_sm.return_value.recover_pending = AsyncMock(return_value=(2, 1))
				with patch("imbalance.server.ModelRouter"):
					with patch("imbalance.server.ImbalanceDaemon._process_flush_queue"):
						with patch("imbalance.server.ImbalanceDaemon._check_notifications"):
							await daemon.startup()


@pytest.mark.asyncio
async def test_process_flush_queue_exception():
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	daemon.db = AsyncMock()
	mock_router = AsyncMock()
	mock_router.complete = AsyncMock(side_effect=Exception("llm error"))
	mock_router.apply_delta = AsyncMock()
	daemon._router = mock_router

	mock_item = MagicMock()
	mock_item.id = 1
	mock_item.session_id = "test-session"
	mock_item.payload = b'{"summary": "test", "decisions": [], "next_steps": []}'
	mock_item.attempts = 0

	with patch("imbalance.server.FlushQueue") as mock_queue_cls:
		mock_queue = AsyncMock()
		mock_queue.due = AsyncMock(return_value=[mock_item])
		mock_queue.mark_failed = AsyncMock(return_value="2024-01-01")
		mock_queue_cls.return_value = mock_queue
		with patch("imbalance.server.FlushPayload") as mock_payload:
			mock_payload.from_json = MagicMock(return_value=MagicMock())
			await daemon._process_flush_queue()


@pytest.mark.asyncio
async def test_process_flush_queue_without_session_manager():
	from imbalance.core.project import Project, ProjectConfig
	config = ProjectConfig(name="test", version="1")
	project = Project(root=Path("/tmp"), config_path=Path("/tmp/test.toml"), config=config, data_dir=Path("/tmp"))
	daemon = ImbalanceDaemon(project)
	daemon.db = AsyncMock()
	mock_router = AsyncMock()
	mock_router.complete = AsyncMock(return_value="delta")
	mock_router.apply_delta = AsyncMock()
	daemon._router = mock_router
	daemon.session_manager = None

	mock_item = MagicMock()
	mock_item.id = 1
	mock_item.session_id = "test-session"
	mock_item.payload = b'{"summary": "test", "decisions": [], "next_steps": []}'
	mock_item.attempts = 0

	with patch("imbalance.server.FlushQueue") as mock_queue_cls:
		mock_queue = AsyncMock()
		mock_queue.due = AsyncMock(return_value=[mock_item])
		mock_queue.complete = AsyncMock()
		mock_queue_cls.return_value = mock_queue
		with patch("imbalance.server.FlushPayload") as mock_payload:
			mock_payload.from_json = MagicMock(return_value=MagicMock())
			await daemon._process_flush_queue()