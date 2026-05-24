from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import signal
from pathlib import Path
from typing import TYPE_CHECKING

import aiosqlite

from imbalance.core.project import Project, load_project
from imbalance.core.queue import FlushQueue
from imbalance.core.router import ModelRouter
from imbalance.core.session import FlushPayload, SessionManager
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
		self._shutting_down = False
		self._shutdown_lock = asyncio.Lock()
		self._router: ModelRouter | None = None

	async def startup(self) -> None:
		try:
			self.db = await open_db(self.project.db_path)
			await run_migrations(self.db)
		except Exception:
			if self.db:
				await self.db.close()
			raise
		self.session_manager = SessionManager(
			db=self.db,
			kb_name=self.project.name,
			pending_dir=self.project.kb_dir / 'pending',
		)
		recovered, failed = await self.session_manager.recover_pending()
		if recovered or failed:
			logger.info(f'Session recovery: {recovered} recovered, {failed} failed')

		self._router = ModelRouter()
		await self._process_flush_queue()

		PID_FILE.parent.mkdir(parents=True, exist_ok=True)
		PID_FILE.write_text(str(os.getpid()))

	async def _process_flush_queue(self) -> None:
		if not self.db:
			return
		queue = FlushQueue(self.db)
		due = await queue.due(limit=5)
		for item in due:
			if not self._router:
				break
			try:
				payload = FlushPayload.from_json(item.payload)
				delta = await self._router.complete(
					f'Summarize: {payload.summary}\nDecisions: {payload.decisions}\nNext: {payload.next_steps}',
					max_tokens=600,
				)
				await self._router.apply_delta(delta, self.db)
				if self.session_manager:
					await self.session_manager.mark_flushed(item.session_id)
				await queue.complete(item.id)
				logger.info(f'Processed queued flush for session {item.session_id}')
			except Exception as e:
				next_retry = await queue.mark_failed(item.id, item.attempts + 1, str(e))
				logger.warning(f'Flush for {item.session_id} failed, retry at {next_retry}: {e}')

	async def shutdown(self) -> None:
		async with self._shutdown_lock:
			if self._shutting_down:
				return
			self._shutting_down = True

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
			try:
				await checkpoint(self.db, mode='FULL')
			except Exception:
				logger.exception('WAL checkpoint failed')
			finally:
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
	try:
		await daemon.startup()
	except Exception:
		await daemon.shutdown()
		raise

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
	try:
		await daemon._server.serve()
	finally:
		await daemon.shutdown()
