from __future__ import annotations

import asyncio
import signal
from pathlib import Path
from typing import Annotated

import typer

from imbalance.core.project import Project, find_project_config, load_project
from imbalance.core.query import QueryEngine
from imbalance.core.queue import FlushQueue
from imbalance.core.session import FlushPayload, SessionManager
from imbalance.core.write import WriteEngine
from imbalance.storage.db import integrity_check, open_db, run_migrations
from imbalance.storage.store import SQLiteStore

app = typer.Typer(help='SQLite-first context memory for coding agents.')
project_app = typer.Typer(help='Project commands.')
session_app = typer.Typer(help='Session checkpoint and recovery commands.')
queue_app = typer.Typer(help='Durable flush queue commands.')
daemon_app = typer.Typer(help='Daemon commands.')
embeddings_app = typer.Typer(help='Embedding tier management.')
app.add_typer(project_app, name='project')
app.add_typer(session_app, name='session')
app.add_typer(queue_app, name='queue')
app.add_typer(daemon_app, name='daemon')
app.add_typer(embeddings_app, name='embeddings')


@project_app.command('info')
def project_info() -> None:
	project = load_project()
	typer.echo(f'name: {project.name}')
	typer.echo(f'config: {project.config_path}')
	typer.echo(f'kb_dir: {project.kb_dir}')
	typer.echo(f'db_path: {project.db_path}')


@project_app.command('init')
def project_init(
	name: Annotated[str | None, typer.Option('--name')] = None,
	force: Annotated[bool, typer.Option('--force')] = False,
) -> None:
	path = Path.cwd() / 'imbalance.toml'
	if path.exists() and not force:
		raise typer.BadParameter(f'{path} already exists; pass --force to overwrite')
	project_name = name or Path.cwd().name
	path.write_text(
		'\n'.join(
			[
				'[project]',
				f'name = "{project_name}"',
				'version = "1"',
				'',
				'[kb]',
				f'store = "{project_name}"',
				'',
				'[retrieval]',
				'budget_tokens = 2000',
				'',
			]
		),
		encoding='utf-8',
	)
	typer.echo(f'created {path}')


@app.command('init-db')
def init_db() -> None:
	asyncio.run(_init_db())


@app.command('doctor')
def doctor() -> None:
	asyncio.run(_doctor())


@app.command('save-fact')
def save_fact(
	content: Annotated[str, typer.Argument()],
	section: Annotated[str, typer.Option('--section')] = 'context',
	slug: Annotated[str | None, typer.Option('--slug')] = None,
	tag: Annotated[list[str] | None, typer.Option('--tag')] = None,
	session_id: Annotated[str | None, typer.Option('--session-id')] = None,
) -> None:
	asyncio.run(
		_save_fact(
			content=content,
			section=section,
			slug=slug,
			tags=tag or [],
			session_id=session_id,
		)
	)


@app.command('search')
def search(
	query: Annotated[str, typer.Argument()],
	budget: Annotated[int, typer.Option('--budget')] = 2000,
	scope: Annotated[list[str] | None, typer.Option('--scope')] = None,
) -> None:
	asyncio.run(_search(query=query, budget=budget, scope=scope))


@session_app.command('start')
def session_start() -> None:
	asyncio.run(_session_start())


@session_app.command('checkpoint')
def session_checkpoint(
	session_id: Annotated[str, typer.Argument()],
	summary: Annotated[str, typer.Option('--summary')],
	decision: Annotated[list[str] | None, typer.Option('--decision')] = None,
	next_step: Annotated[list[str] | None, typer.Option('--next-step')] = None,
) -> None:
	asyncio.run(
		_session_checkpoint(
			session_id=session_id,
			summary=summary,
			decisions=decision or [],
			next_steps=next_step or [],
		)
	)


@session_app.command('list')
def session_list() -> None:
	asyncio.run(_session_list())


@session_app.command('flush')
def session_flush(
	session_id: Annotated[str, typer.Argument()],
	summary: Annotated[str, typer.Option('--summary')],
	decision: Annotated[list[str] | None, typer.Option('--decision')] = None,
	next_step: Annotated[list[str] | None, typer.Option('--next-step')] = None,
) -> None:
	asyncio.run(
		_session_flush(
			session_id=session_id,
			summary=summary,
			decisions=decision or [],
			next_steps=next_step or [],
		)
	)


@queue_app.command('recover')
def queue_recover() -> None:
	asyncio.run(_queue_recover())


@queue_app.command('status')
def queue_status() -> None:
	asyncio.run(_queue_status())


@queue_app.command('retry')
def queue_retry(
	session_id: Annotated[str | None, typer.Argument()] = None,
) -> None:
	asyncio.run(_queue_retry(session_id))


@daemon_app.command('start')
def daemon_start(
	port: Annotated[int, typer.Option('--port')] = 4731,
) -> None:
	asyncio.run(_daemon_start(port))


@daemon_app.command('stop')
def daemon_stop() -> None:
	try:
		from imbalance.server import PID_FILE
	except ImportError:
		typer.echo('Daemon PID file path unavailable')
		raise typer.Exit(code=1) from None

	if not PID_FILE.exists():
		typer.echo('No daemon PID file found')
		raise typer.Exit(code=1)

	try:
		pid = int(PID_FILE.read_text().strip())
	except (ValueError, OSError):
		typer.echo('Invalid PID file')
		raise typer.Exit(code=1) from None

	try:
		import os

		os.kill(pid, signal.SIGTERM)
		typer.echo(f'Sent SIGTERM to daemon (PID {pid})')
	except ProcessLookupError:
		typer.echo(f'Daemon process {pid} not found')
		PID_FILE.unlink(missing_ok=True)
		raise typer.Exit(code=1) from None
	except PermissionError:
		typer.echo(f'Permission denied to kill process {pid}')
		raise typer.Exit(code=1) from None


async def _daemon_start(port: int) -> None:
	from imbalance.server import run_daemon

	await run_daemon(port)


async def _init_db() -> None:
	project = load_project()
	db = await _open_project_db(project)
	await db.close()
	typer.echo(f'initialized {project.db_path}')


async def _doctor() -> None:
	config = find_project_config()
	if config is None:
		typer.echo('config: missing')
		raise typer.Exit(code=20)
	project = Project.from_toml(config)
	db = await _open_project_db(project)
	check = await integrity_check(db)
	queue_count = await FlushQueue(db).count()
	sessions = await _session_manager(db, project).list()
	await db.close()
	typer.echo(f'config: {config}')
	typer.echo(f'db: {project.db_path}')
	typer.echo(f'integrity: {check}')
	typer.echo(f'sessions: {len(sessions)}')
	typer.echo(f'pending_queue: {queue_count}')


async def _save_fact(
	content: str,
	section: str,
	slug: str | None,
	tags: list[str],
	session_id: str | None,
) -> None:
	project = load_project()
	db = await _open_project_db(project)
	store = SQLiteStore(db, project.name)
	result = await WriteEngine(store).save_fact(
		content=content,
		section=section,
		slug=slug,
		tags=tags,
		session_id=session_id,
	)
	await db.close()
	typer.echo(f'saved {result.slug} ({result.token_count} tokens)')


async def _search(query: str, budget: int, scope: list[str] | None) -> None:
	project = load_project()
	db = await _open_project_db(project)
	store = SQLiteStore(db, project.name)
	pack = await QueryEngine(store).get_context_pack(
		query,
		budget_tokens=budget,
		scope=scope,
	)
	await db.close()
	typer.echo(pack.render_markdown())


async def _session_start() -> None:
	project = load_project()
	db = await _open_project_db(project)
	session = await _session_manager(db, project).start()
	await db.close()
	typer.echo(session.id)


async def _session_checkpoint(
	session_id: str,
	summary: str,
	decisions: list[str],
	next_steps: list[str],
) -> None:
	project = load_project()
	db = await _open_project_db(project)
	manager = _session_manager(db, project)
	path = await manager.prepare_flush(
		session_id,
		FlushPayload(summary=summary, decisions=decisions, next_steps=next_steps),
	)
	await manager.enqueue_pending(session_id)
	await db.close()
	typer.echo(f'checkpointed {session_id}: {path}')


async def _session_list() -> None:
	project = load_project()
	db = await _open_project_db(project)
	sessions = await _session_manager(db, project).list()
	await db.close()
	for session in sessions:
		typer.echo(f'{session.id}\t{session.status.value}\t{session.log_path or "-"}')


async def _session_flush(
	session_id: str,
	summary: str,
	decisions: list[str],
	next_steps: list[str],
) -> None:
	project = load_project()
	db = await _open_project_db(project)
	try:
		manager = _session_manager(db, project)
		await manager.flush(
			session_id,
			FlushPayload(summary=summary, decisions=decisions, next_steps=next_steps),
		)
	finally:
		await db.close()
	typer.echo(f'flushed {session_id}')


async def _queue_recover() -> None:
	project = load_project()
	db = await _open_project_db(project)
	recovered, failed = await _session_manager(db, project).recover_pending()
	await db.close()
	typer.echo(f'recovered: {recovered}')
	typer.echo(f'failed: {failed}')


async def _queue_status() -> None:
	project = load_project()
	db = await _open_project_db(project)
	queue = FlushQueue(db)
	items = await queue.items(limit=100)
	count = await queue.count()
	await db.close()
	typer.echo(f'queued: {count}')
	for item in items:
		typer.echo(f'{item.session_id}\tattempts={item.attempts}\tnext_retry={item.next_retry}')


async def _queue_retry(session_id: str | None) -> None:
	project = load_project()
	db = await _open_project_db(project)
	try:
		queue = FlushQueue(db)
		if session_id:
			await queue.reset_retry(session_id)
			typer.echo(f'reset retry for session {session_id}')
		else:
			recovered = await queue.reset_all_retries()
			typer.echo(f'reset {recovered} items')
	finally:
		await db.close()


@app.command('claude-code')
def claude_code_setup() -> None:
	"""Auto-configure Claude Code settings.json for imbalance MCP."""
	asyncio.run(_claude_code_setup())


@app.command('mcp')
def mcp() -> None:
	"""Run the MCP server."""
	from imbalance.mcp.server import main

	asyncio.run(main())


async def _claude_code_setup() -> None:
	import json
	from pathlib import Path

	config_path = Path.home() / '.config' / 'claude-code' / 'settings.json'
	config_path.parent.mkdir(parents=True, exist_ok=True)

	settings: dict[str, object] = {}
	if config_path.exists():
		settings = json.loads(config_path.read_text())

	mcp_servers = settings.setdefault('mcpServers', {})
	mcp_servers['imbalance'] = {
		'command': 'imbalance',
		'args': ['mcp'],
	}

	config_path.write_text(json.dumps(settings, indent=2) + '\n')
	typer.echo(f'Claude Code configured: {config_path}')
	project = load_project()
	await _open_project_db(project)
	project.kb_dir.mkdir(parents=True, exist_ok=True)
	(project.kb_dir / 'pending').mkdir(parents=True, exist_ok=True)
	typer.echo('Ready for imbalance MCP')


async def _open_project_db(project: Project):
	db = await open_db(project.db_path)
	await run_migrations(db)
	return db


def _session_manager(db, project: Project) -> SessionManager:
	return SessionManager(db=db, kb_name=project.name, pending_dir=project.kb_dir / 'pending')


@embeddings_app.command('status')
def embeddings_status() -> None:
	asyncio.run(_embeddings_status())


async def _embeddings_status() -> None:
	project = load_project()
	db = await _open_project_db(project)
	try:
		from imbalance.storage.vec import is_vec_available

		vec_ok = await is_vec_available(db)
		rows = await db.execute_fetchall(
			'SELECT COUNT(*) as cnt FROM wiki_sections WHERE kb_name=? AND archived=FALSE',
			(project.name,),
		)
		wiki_count = rows[0]['cnt'] if rows else 0

		vec_rows = await db.execute_fetchall('SELECT COUNT(*) as cnt FROM wiki_vec')
		vec_count = vec_rows[0]['cnt'] if vec_rows else 0

		if vec_ok and vec_count > 0:
			typer.echo('tier: 1/2 (sqlite-vec enabled)')
			typer.echo(f'vectors indexed: {vec_count}')
		else:
			typer.echo('tier: 0 (FTS5-only)')
		typer.echo(f'wiki sections: {wiki_count}')
		typer.echo(f'sqlite-vec available: {vec_ok}')
	finally:
		await db.close()


@embeddings_app.command('set')
def embeddings_set(
	provider: Annotated[str, typer.Argument(help='ollama|openai|openrouter|none')],
	model: Annotated[str | None, typer.Option('--model')] = None,
) -> None:
	asyncio.run(_embeddings_set(provider, model))


async def _embeddings_set(provider: str, model: str | None) -> None:
	import tomllib

	project = load_project()
	config_path = project.config_path
	raw = tomllib.loads(config_path.read_text(encoding='utf-8'))

	if provider == 'none':
		raw.pop('embeddings', None)
	elif provider == 'ollama':
		raw['embeddings'] = {
			'provider': 'ollama',
			'model': model or 'nomic-embed-text:v1.5',
		}
	elif provider in ('openai', 'openrouter'):
		raw['embeddings'] = {
			'provider': provider,
			'model': model or 'text-embedding-3-small',
		}
	else:
		raise typer.BadParameter(f'Unknown provider: {provider}')

	import re

	content = config_path.read_text(encoding='utf-8')
	if 'embeddings' in raw:
		emb = raw['embeddings']
		block = '[embeddings]\n'
		for k, v in emb.items():
			block += f'{k} = "{v}"\n'
		if '[embeddings]' in content:
			content = re.sub(r'\[embeddings\].*?(?=\n\[|\Z)', block.strip(), content, flags=re.DOTALL)
		else:
			content = content.rstrip() + '\n\n' + block
	else:
		content = re.sub(r'\[embeddings\].*?(?=\n\[|\Z)', '', content, flags=re.DOTALL)

	config_path.write_text(content.strip() + '\n', encoding='utf-8')
	typer.echo(f'Embedding provider set to: {provider}')

	if provider != 'none':
		typer.echo('Run `imbalance embeddings reindex` to build vectors.')


if __name__ == '__main__':
	app()
