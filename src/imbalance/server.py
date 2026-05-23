from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
from pathlib import Path
from typing import TYPE_CHECKING

import aiosqlite

from imbalance.core.project import Project, load_project
from imbalance.core.session import SessionManager
from imbalance.storage.db import checkpoint, open_db, run_migrations

if TYPE_CHECKING:
	from uvicorn import Server

logger = logging.getLogger(__name__)

PID_FILE = Path.home() / '.config' / 'imbalance' / 'daemon.pid'


class ImbalanceDaemon:
	def __init__(self, project: Project) -> None:
		self.project = project
		self.db: aiosqlite.Connection | None = None
		self.session_manager: SessionManager | None = None
		self._accepting = True
		self._in_flight: set[asyncio.Task[object]] = set()
		self._server: Server | None = None

	async def startup(self) -> None:
		self.db = await open_db(self.project.db_path)
		await run_migrations(self.db)
		self.session_manager = SessionManager(
			db=self.db,
			kb_name=self.project.name,
			pending_dir=self.project.kb_dir / 'pending',
		)
		recovered, failed = await self.session_manager.recover_pending()
		if recovered or failed:
			logger.info(f'Session recovery: {recovered} recovered, {failed} failed')

		PID_FILE.parent.mkdir(parents=True, exist_ok=True)
		PID_FILE.write_text(str(asyncio.get_event_loop()._process_pid or 0))

	async def shutdown(self) -> None:
		logger.info('Shutting down gracefully...')
		self._accepting = False

		if self._in_flight:
			try:
				await asyncio.wait_for(
					asyncio.gather(*self._in_flight, return_exceptions=True),
					timeout=10.0,
				)
			except TimeoutError:
				logger.warning('In-flight drain timed out')

		if self.db:
			await checkpoint(self.db, mode='FULL')
			await self.db.close()

		with contextlib.suppress(Exception):
			PID_FILE.unlink(missing_ok=True)

	def register_signal_handlers(self) -> None:
		loop = asyncio.get_event_loop()
		with contextlib.suppress(NotImplementedError):
			for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
				loop.add_signal_handler(
					sig, lambda s=sig: asyncio.create_task(self._handle_signal(s))
				)

	async def _handle_signal(self, sig: signal.Signals) -> None:
		logger.info(f'Received {sig.name}')
		await self.shutdown()
		if self._server:
			self._server.should_exit = True


async def run_daemon(port: int = 4731) -> None:
	project = load_project()
	daemon = ImbalanceDaemon(project)
	await daemon.startup()

	from uvicorn import Config, Server

	config = Config(
		app='imbalance.api.app:create_app',
		factory=True,
		host='0.0.0.0',
		port=port,
		log_level='info',
	)
	daemon._server = Server(config)
	daemon.register_signal_handlers()
	await daemon._server.serve()
