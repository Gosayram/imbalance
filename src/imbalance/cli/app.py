from __future__ import annotations

import asyncio
import os
import signal
from pathlib import Path
from typing import Annotated

import typer

from imbalance.core.project import Project, find_project_config, load_project
from imbalance.core.query import QueryEngine
from imbalance.core.queue import FlushQueue
from imbalance.core.router import ModelRouter
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
kb_app = typer.Typer(help='Knowledge base compaction commands.')
wiki_app = typer.Typer(help='Wiki section commands.')
app.add_typer(project_app, name='project')
app.add_typer(session_app, name='session')
app.add_typer(queue_app, name='queue')
app.add_typer(daemon_app, name='daemon')
app.add_typer(embeddings_app, name='embeddings')
app.add_typer(kb_app, name='kb')
app.add_typer(wiki_app, name='wiki')


def _get_openrouter_key() -> str | None:
	return os.environ.get('OPENROUTER_API_KEY')


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


@daemon_app.command('install')
def daemon_install() -> None:
	"""Install daemon as system service (launchd on macOS, systemd on Linux)."""
	import sys

	if sys.platform == 'darwin':
		_install_launchd()
	elif sys.platform.startswith('linux'):
		_install_systemd()
	else:
		typer.echo(f'Unsupported platform: {sys.platform}')
		raise typer.Exit(code=1)


def _install_launchd() -> None:
	import shutil
	from pathlib import Path

	imbalance_bin = shutil.which('imbalance')
	if not imbalance_bin:
		typer.echo('imbalance binary not found in PATH')
		raise typer.Exit(code=1)

	plist = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>ai.imbalance.daemon</string>
    <key>ProgramArguments</key><array>
        <string>{imbalance_bin}</string><string>daemon</string><string>start</string>
    </array>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardOutPath</key><string>/tmp/imbalance-daemon.log</string>
    <key>StandardErrorPath</key><string>/tmp/imbalance-daemon.err</string>
</dict>
</plist>'''

	plist_path = Path.home() / 'Library' / 'LaunchAgents' / 'ai.imbalance.daemon.plist'
	plist_path.parent.mkdir(parents=True, exist_ok=True)
	plist_path.write_text(plist)
	typer.echo(f'Installed launchd plist: {plist_path}')
	typer.echo('Run: launchctl load ' + str(plist_path))


def _install_systemd() -> None:
	import shutil
	from pathlib import Path

	imbalance_bin = shutil.which('imbalance')
	if not imbalance_bin:
		typer.echo('imbalance binary not found in PATH')
		raise typer.Exit(code=1)

	unit = f'''[Unit]
Description=imbalance knowledge base daemon
After=network.target

[Service]
Type=simple
ExecStart={imbalance_bin} daemon start
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
'''

	unit_path = Path.home() / '.config' / 'systemd' / 'user' / 'imbalance.service'
	unit_path.parent.mkdir(parents=True, exist_ok=True)
	unit_path.write_text(unit)
	typer.echo(f'Installed systemd unit: {unit_path}')
	typer.echo('Run: systemctl --user enable --now imbalance')


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
	router = ModelRouter(openrouter_key=_get_openrouter_key())
	engine = WriteEngine(store, router)
	result = await engine.save_fact(
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


@app.command('setup')
def setup_all_agents(
	agent: Annotated[str | None, typer.Option('--agent', help='Specific agent: claude|cursor|codex|gemini|windsurf|copilot|all')] = None,
	force: Annotated[bool, typer.Option('--force')] = False,
	mcp_configs: Annotated[bool, typer.Option('--mcp-configs')] = False,
	skills: Annotated[bool, typer.Option('--skills')] = False,
	report: Annotated[bool, typer.Option('--report')] = False,
) -> None:
	"""Generate agent files for all supported agents. Creates AGENTS.md as primary."""
	asyncio.run(_setup_all_agents(agent, force, mcp_configs, skills, report))


@app.command('claude-code')
def claude_code_setup(
	template: Annotated[
		str | None,
		typer.Option('--template', help='python-backend|frontend-react|devops|data-science'),
	] = None,
) -> None:
	"""Auto-configure Claude Code settings.json for imbalance MCP."""
	asyncio.run(_claude_code_setup(template))


@app.command('hook')
def hook(
	hook_type: Annotated[str, typer.Argument(help='session-start|session-stop|prompt-submit')],
	auto_flush: Annotated[bool, typer.Option('--auto-flush')] = False,
	project_from_cwd: Annotated[bool, typer.Option('--project-from-cwd')] = False,
	check_budget: Annotated[bool, typer.Option('--check-budget')] = False,
) -> None:
	"""Run native hooks for agent integration."""
	asyncio.run(_run_hook(hook_type, auto_flush, project_from_cwd, check_budget))


@app.command('mcp')
def mcp() -> None:
	"""Run the MCP server."""
	from imbalance.mcp.server import main

	asyncio.run(main())


async def _claude_code_setup(template: str | None) -> None:
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
	db = await _open_project_db(project)
	try:
		project.kb_dir.mkdir(parents=True, exist_ok=True)
		(project.kb_dir / 'pending').mkdir(parents=True, exist_ok=True)
	finally:
		await db.close()

	if template:
		from imbalance.core.templates import generate_claude_md

		content = generate_claude_md(template, project_name=project.name)
		claude_path = Path.cwd() / 'CLAUDE.md'
		claude_path.write_text(content, encoding='utf-8')
		typer.echo(f'Generated CLAUDE.md from template: {template}')

	typer.echo('Ready for imbalance MCP')


async def _run_hook(
	hook_type: str, auto_flush: bool, project_from_cwd: bool, check_budget: bool
) -> None:
	project = load_project()
	db = await _open_project_db(project)
	try:
		if hook_type == 'session-start':
			typer.echo('Session initialized. Call get_context("current task") to load context.')
		elif hook_type == 'session-stop':
			if auto_flush:
				session = await db.execute_fetchone(
					'SELECT id FROM sessions WHERE kb_name=? AND status="active" ORDER BY updated_at DESC LIMIT 1',
					(project.name,),
				)
				if session:
					typer.echo(f'Flushing session {session["id"]}...')
					await db.execute(
						"UPDATE sessions SET status='flushed' WHERE id=?",
						(session['id'],),
					)
					await db.commit()
		elif hook_type == 'prompt-submit':
			if check_budget:
				from imbalance.core.budget import SessionBudgetMonitor

				monitor = SessionBudgetMonitor()
				action = monitor.check(used_tokens=1500, total_tokens=20000)
				if action.action == 'warn':
					typer.echo(f'[imbalance] Context at {action.action}. Call save_fact() for key findings.')
		else:
			raise ValueError(f'Unknown hook type: {hook_type}')
	finally:
		await db.close()


async def _open_project_db(project: Project):
	db = await open_db(project.db_path)
	await run_migrations(db)
	return db


def _session_manager(db, project: Project) -> SessionManager:
	return SessionManager(db=db, kb_name=project.name, pending_dir=project.kb_dir / 'pending')


@embeddings_app.command('status')
def embeddings_status() -> None:
	asyncio.run(_embeddings_status())


async def _setup_all_agents(
	agent: str | None, force: bool, mcp_configs: bool, skills: bool, report: bool
) -> None:
	"""Generate agent files for all supported agents."""
	from imbalance.core.templates import (
		generate_agents_md,
		generate_copilot_section,
		generate_cursor_mdc,
		generate_gemini_md,
	)

	project = load_project()
	cwd = Path.cwd()
	agents_list = agent.split(',') if agent else ['all']

	generated = []
	skipped = []
	warnings = []

	# Generate AGENTS.md as primary
	agents_content = generate_agents_md(project.name)
	agents_path = cwd / 'AGENTS.md'
	if not agents_path.exists() or force:
		agents_path.write_text(agents_content, encoding='utf-8')
		generated.append({'agent': 'codex', 'path': 'AGENTS.md', 'mode': 'created'})
	else:
		skipped.append({'agent': 'codex', 'reason': 'exists'})

	if 'all' in agents_list or 'claude' in agents_list or 'gemini' in agents_list:
		_claude_path = cwd / 'CLAUDE.md'
		if _claude_path.exists() and not force and not _is_managed_file(_claude_path):
			_append_section(_claude_path, agents_content)
			generated.append({'agent': 'claude', 'path': 'CLAUDE.md', 'mode': 'section-appended'})
		else:
			try:
				_claude_path.symlink_to(agents_path)
				generated.append({'agent': 'claude', 'path': 'CLAUDE.md', 'mode': 'linked'})
				typer.echo('Linked AGENTS.md -> CLAUDE.md')
			except OSError:
				_claude_path.write_text(agents_content, encoding='utf-8')
				generated.append({'agent': 'claude', 'path': 'CLAUDE.md', 'mode': 'created'})

		_gemini_path = cwd / 'GEMINI.md'
		if _gemini_path.exists() and not force and not _is_managed_file(_gemini_path):
			_append_section(_gemini_path, agents_content)
			generated.append({'agent': 'gemini', 'path': 'GEMINI.md', 'mode': 'section-appended'})
		else:
			try:
				_gemini_path.symlink_to(agents_path)
				generated.append({'agent': 'gemini', 'path': 'GEMINI.md', 'mode': 'linked'})
				typer.echo('Linked AGENTS.md -> GEMINI.md')
			except OSError:
				_gemini_path.write_text(generate_gemini_md(project.name), encoding='utf-8')

	if 'all' in agents_list or 'cursor' in agents_list:
		cursor_dir = cwd / '.cursor' / 'rules'
		cursor_dir.mkdir(parents=True, exist_ok=True)
		(cursor_dir / 'imbalance.mdc').write_text(generate_cursor_mdc(project.name), encoding='utf-8')
		generated.append({'agent': 'cursor', 'path': '.cursor/rules/imbalance.mdc', 'mode': 'created'})
		typer.echo('Created .cursor/rules/imbalance.mdc')

	if 'all' in agents_list or 'copilot' in agents_list:
		copilot_file = cwd / '.github' / 'copilot-instructions.md'
		copilot_file.parent.mkdir(parents=True, exist_ok=True)
		_append_section(copilot_file, generate_copilot_section(project.name))
		generated.append({'agent': 'copilot', 'path': '.github/copilot-instructions.md', 'mode': 'updated'})
		typer.echo('Updated .github/copilot-instructions.md')

	if 'all' in agents_list or 'codex' in agents_list:
		typer.echo('AGENTS.md is the primary file for Codex CLI')

	if skills and ('all' in agents_list or 'claude' in agents_list):
		_skills_dir = Path.home() / '.claude' / 'skills'
		_skills_dir.mkdir(parents=True, exist_ok=True)
		(_skills_dir / 'imbalance-load' / 'SKILL.md').parent.mkdir(parents=True, exist_ok=True)
		(_skills_dir / 'imbalance-load' / 'SKILL.md').write_text(
			'---\nname: imbalance-load\ndescription: Load project context from imbalance KB\n---\n'
			'Call `get_context` MCP tool with current task.\nBudget: 2000 tokens.',
			encoding='utf-8',
		)
		(_skills_dir / 'imbalance-flush' / 'SKILL.md').parent.mkdir(parents=True, exist_ok=True)
		(_skills_dir / 'imbalance-flush' / 'SKILL.md').write_text(
			'---\nname: imbalance-flush\ndescription: Save session to KB\n---\n'
			'1. Call `flush_session` with summary, decisions, next_steps.\n2. Confirm session saved.',
			encoding='utf-8',
		)
		typer.echo('Created ~/.claude/skills/imbalance-load and imbalance-flush skills')

	if skills and ('all' in agents_list or 'codex' in agents_list):
		_codex_skills_dir = Path.home() / '.agents' / 'skills'
		_codex_skills_dir.mkdir(parents=True, exist_ok=True)
		(_codex_skills_dir / 'imbalance-load' / 'SKILL.md').parent.mkdir(parents=True, exist_ok=True)
		(_codex_skills_dir / 'imbalance-load' / 'SKILL.md').write_text(
			'---\nname: imbalance-load\ndescription: Load project context\n---\n'
			'Call get_context with task description. Budget: 2000 tokens.',
			encoding='utf-8',
		)
		typer.echo('Created ~/.agents/skills/imbalance-load skill for Codex')

	# MCP config generation
	if mcp_configs and ('all' in agents_list or 'cursor' in agents_list):
		_mcp_config(cwd)

	if report:
		import json

		report_data = {'ok': True, 'generated': generated, 'skipped': skipped, 'warnings': warnings, 'errors': []}
		typer.echo(json.dumps(report_data, indent=2))


def _mcp_config(cwd: Path) -> None:
	"""Generate MCP config files for all detected agents."""
	import json

	# Cursor: .cursor/mcp.json
	cursor_mcp = cwd / '.cursor' / 'mcp.json'
	cursor_mcp.parent.mkdir(parents=True, exist_ok=True)
	existing = json.loads(cursor_mcp.read_text()) if cursor_mcp.exists() else {}
	servers = existing.setdefault('mcpServers', {})
	servers['imbalance'] = {'url': 'http://localhost:4731/mcp/sse'}
	cursor_mcp.write_text(json.dumps(existing, indent=2) + '\n')
	typer.echo('Updated .cursor/mcp.json')

	# VSCode/Cline: .vscode/settings.json
	vsc_settings = cwd / '.vscode' / 'settings.json'
	vsc_settings.parent.mkdir(parents=True, exist_ok=True)
	vsc_existing = json.loads(vsc_settings.read_text()) if vsc_settings.exists() else {}
	cline_servers = vsc_existing.setdefault('cline.mcpServers', {})
	cline_servers['imbalance'] = {'url': 'http://localhost:4731/mcp/sse'}
	vsc_settings.write_text(json.dumps(vsc_existing, indent=2) + '\n')
	typer.echo('Updated .vscode/settings.json')


def _is_managed_file(path: Path) -> bool:
	try:
		content = path.read_text()
		return '<!-- managed by imbalance' in content
	except Exception:
		return False


def _append_section(path: Path, section: str) -> None:
	content = path.read_text() if path.exists() else ''
	marker = '<!-- imbalance -->'
	if marker not in content:
		path.write_text(content + '\n\n' + section, encoding='utf-8')


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


@kb_app.command('compact')
def kb_compact(
	dry_run: Annotated[bool, typer.Option('--dry-run')] = False,
) -> None:
	asyncio.run(_kb_compact(dry_run))


async def _kb_compact(dry_run: bool) -> None:
	from imbalance.core.compaction import KBCompactor

	project = load_project()
	db = await _open_project_db(project)
	try:
		router = ModelRouter()
		compactor = KBCompactor(db=db, router=router, kb_name=project.name)
		report = await compactor.run_full_compaction(dry_run=dry_run)
		typer.echo(f'Compaction complete (dry_run={dry_run}):')
		typer.echo(f'  updated: {len(report.updated)}')
		typer.echo(f'  archived: {len(report.archived)}')
		typer.echo(f'  evergreen: {len(report.evergreen)}')
		typer.echo(f'  current: {len(report.current)}')
	finally:
		await db.close()


@kb_app.command('status')
def kb_status() -> None:
	asyncio.run(_kb_status())


async def _kb_status() -> None:
	project = load_project()
	db = await _open_project_db(project)
	try:
		rows = await db.execute_fetchall(
			'SELECT COUNT(*) as cnt FROM wiki_sections WHERE kb_name=? AND archived=FALSE',
			(project.name,),
		)
		active = rows[0]['cnt'] if rows else 0
		archived = await db.execute_fetchall(
			'SELECT COUNT(*) as cnt FROM wiki_sections WHERE kb_name=? AND archived=TRUE',
			(project.name,),
		)
		archived_cnt = archived[0]['cnt'] if archived else 0
		last = await db.execute_fetchall(
			'SELECT ran_at, sections_total, sections_archived, duration_sec '
			'FROM kb_compaction_log WHERE kb_name=? ORDER BY ran_at DESC LIMIT 1',
			(project.name,),
		)
		typer.echo(f'Active sections: {active}')
		typer.echo(f'Archived: {archived_cnt}')
		if last:
			r = last[0]
			typer.echo(f'Last compaction: {r["ran_at"]} ({r["sections_total"]} total, {r["sections_archived"]} archived, {r["duration_sec"]:.1f}s)')
		else:
			typer.echo('No compaction runs recorded')
	finally:
		await db.close()


@wiki_app.command('show')
def wiki_show(
	slug: Annotated[str, typer.Argument(help='Section slug')],
	include_archived: Annotated[bool, typer.Option('--include-archived')] = False,
) -> None:
	asyncio.run(_wiki_show(slug, include_archived))


async def _wiki_show(slug: str, include_archived: bool) -> None:
	project = load_project()
	db = await _open_project_db(project)
	try:
		extra = '' if include_archived else 'AND archived=FALSE'
		rows = await db.execute_fetchall(
			f'SELECT content, section, token_count, updated_at FROM wiki_sections '
			f'WHERE kb_name=? AND slug=? {extra}',
			(project.name, slug),
		)
		if not rows:
			typer.echo(f'Section not found: {slug}')
			raise typer.Exit(code=1)
		r = rows[0]
		typer.echo(f'[{r["section"]}] {slug} ({r["token_count"]} tokens, {r["updated_at"]})')
		typer.echo(r['content'])
	finally:
		await db.close()


@wiki_app.command('restore')
def wiki_restore(
	slug: Annotated[str, typer.Argument(help='Section slug to restore from archive')],
) -> None:
	asyncio.run(_wiki_restore(slug))


async def _wiki_restore(slug: str) -> None:
	project = load_project()
	db = await _open_project_db(project)
	try:
		await db.execute(
			"UPDATE wiki_sections SET archived=FALSE, archived_at=NULL, archive_reason=NULL "
			"WHERE kb_name=? AND slug=? AND archived=TRUE",
			(project.name, slug),
		)
		await db.commit()
		typer.echo(f'Restored: {slug}')
	finally:
		await db.close()


@wiki_app.command('purge')
def wiki_purge(
	older_than_days: Annotated[int, typer.Option('--older-than', help='Purge archived older than N days')] = 90,
) -> None:
	asyncio.run(_wiki_purge(older_than_days))


async def _wiki_purge(older_than_days: int) -> None:
	project = load_project()
	db = await _open_project_db(project)
	try:
		rows = await db.execute_fetchall(
			"SELECT slug FROM wiki_sections WHERE kb_name=? AND archived=TRUE "
			"AND archived_at < datetime('now', ? || ' days')",
			(project.name, f'-{older_than_days}'),
		)
		if not rows:
			typer.echo('No archived sections to purge')
			return
		for r in rows:
			await db.execute(
				"DELETE FROM wiki_fts WHERE rowid IN (SELECT id FROM wiki_sections WHERE kb_name=? AND slug=?)",
				(project.name, r['slug']),
			)
			await db.execute(
				"DELETE FROM wiki_sections WHERE kb_name=? AND slug=?",
				(project.name, r['slug']),
			)
		await db.commit()
		typer.echo(f'Purged {len(rows)} archived sections')
	finally:
		await db.close()


@app.command('backup')
def backup(
	path: Annotated[str, typer.Argument(help='Output path for backup DB')],
) -> None:
	asyncio.run(_backup(path))


async def _backup(path: str) -> None:
	project = load_project()
	db = await _open_project_db(project)
	try:
		from pathlib import PurePosixPath

		backup_path = str(PurePosixPath(path))
		await db.execute(f"VACUUM INTO '{backup_path}'")
		await db.commit()
		typer.echo(f'Backup created: {backup_path}')
	finally:
		await db.close()


@app.command('health')
def health_cmd() -> None:
	asyncio.run(_health_cmd())


async def _health_cmd() -> None:
	from imbalance.core.project import load_project

	project = load_project()
	db = await _open_project_db(project)
	try:
		check = await integrity_check(db)
		queue_count = await FlushQueue(db).count()

		typer.echo(f'integrity: {check}')
		typer.echo(f'pending_queue: {queue_count}')
		typer.echo(f'kb: {project.name}')
		typer.echo(f'db: {project.db_path}')
	finally:
		await db.close()


@app.command('flush')
def flush_standalone(
	summary: Annotated[str, typer.Option('--summary', help='Session summary text')],
	decision: Annotated[list[str] | None, typer.Option('--decision')] = None,
	next_step: Annotated[list[str] | None, typer.Option('--next-step')] = None,
	session_id: Annotated[str | None, typer.Option('--session-id')] = None,
) -> None:
	"""CI-mode flush: write summary to KB without daemon."""
	asyncio.run(
		_flush_ci(
			summary=summary,
			decisions=decision or [],
			next_steps=next_step or [],
			session_id=session_id,
		)
	)


async def _flush_ci(
	summary: str, decisions: list[str], next_steps: list[str], session_id: str | None
) -> None:
	import uuid

	from imbalance.core.tokens import estimate_tokens
	from imbalance.core.write import WriteEngine

	project = load_project()
	db = await _open_project_db(project)
	try:
		sid = session_id or str(uuid.uuid4())
		store = SQLiteStore(db, project.name)
		engine = WriteEngine(store)
		content = summary
		if decisions:
			content += '\n\nDecisions:\n' + '\n'.join('- ' + d for d in decisions)
		if next_steps:
			content += '\n\nNext steps:\n' + '\n'.join('- ' + s for s in next_steps)
		token_count = estimate_tokens(content)
		await engine.save_fact(
			content=content, section='context', tags=['ci-flush'], session_id=sid
		)
		typer.echo(f'CI flush saved ({token_count} tokens, session {sid})')
	finally:
		await db.close()


@wiki_app.command('link')
def wiki_link(
	source: Annotated[str, typer.Argument(help='Source slug')],
	target: Annotated[str, typer.Argument(help='Target slug')],
	link_type: Annotated[str, typer.Option('--type', help='references|related|depends_on')] = 'references',
) -> None:
	asyncio.run(_wiki_link(source, target, link_type))


async def _wiki_link(source: str, target: str, link_type: str) -> None:
	from imbalance.core.links import create_link

	project = load_project()
	db = await _open_project_db(project)
	try:
		await create_link(db, project.name, source, target, link_type)
		typer.echo(f'Linked {source} → {target} ({link_type})')
	finally:
		await db.close()


@wiki_app.command('unlink')
def wiki_unlink(
	source: Annotated[str, typer.Argument(help='Source slug')],
	target: Annotated[str, typer.Argument(help='Target slug')],
	link_type: Annotated[str, typer.Option('--type')] = 'references',
) -> None:
	asyncio.run(_wiki_unlink(source, target, link_type))


async def _wiki_unlink(source: str, target: str, link_type: str) -> None:
	from imbalance.core.links import remove_link

	project = load_project()
	db = await _open_project_db(project)
	try:
		await remove_link(db, project.name, source, target, link_type)
		typer.echo(f'Removed link {source} → {target}')
	finally:
		await db.close()


@wiki_app.command('conflicts')
def wiki_conflicts() -> None:
	asyncio.run(_wiki_conflicts())


async def _wiki_conflicts() -> None:
	from imbalance.core.conflicts import get_conflicts

	project = load_project()
	db = await _open_project_db(project)
	try:
		conflicts = await get_conflicts(db, project.name)
		if not conflicts:
			typer.echo('No conflicts found')
			return
		for c in conflicts:
			typer.echo(f'{c["source_slug"]} ↔ {c["target_slug"]} ({c["created_at"]})')
	finally:
		await db.close()


@app.command('stats')
def stats_cmd(
	show: Annotated[
		str | None,
		typer.Option('--show', help='slow-queries|token-savings|provider-health'),
	] = None,
) -> None:
	asyncio.run(_stats_cmd(show))


async def _stats_cmd(show: str | None) -> None:
	project = load_project()
	db = await _open_project_db(project)
	try:
		from datetime import UTC, datetime, timedelta

		since = (datetime.now(UTC) - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')

		r = dict((await db.execute_fetchall(
			'SELECT COUNT(*) as cnt, '
			'COALESCE(AVG(latency_ms),0) as avg_ms, '
			'COALESCE(AVG(tokens_returned),0) as avg_tokens '
			'FROM retrieval_log WHERE timestamp >= ?',
			(since,),
		))[0] or {})
		f = dict((await db.execute_fetchall(
			'SELECT COUNT(*) as cnt, '
			'SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as ok, '
			'COALESCE(AVG(latency_ms),0) as avg_ms '
			'FROM flush_log WHERE timestamp >= ?',
			(since,),
		))[0] or {})

		if show == 'slow-queries':
			rows = await db.execute_fetchall(
				'SELECT query, latency_ms FROM retrieval_log WHERE latency_ms > 100 ORDER BY latency_ms DESC LIMIT 10',
			)
			typer.echo('Slow queries (>100ms):')
			for row in rows:
				typer.echo(f'  {row["latency_ms"]}ms: {row["query"][:60]}')
		elif show == 'token-savings':
			rows = await db.execute_fetchall(
				'SELECT SUM(tokens_budget - tokens_returned) as saved FROM retrieval_log WHERE timestamp >= ?',
				(since,),
			)
			saved = rows[0]['saved'] if rows else 0
			typer.echo(f'Token savings (last 30d): {saved}')
		elif show == 'provider-health':
			rows = await db.execute_fetchall(
				'SELECT provider, COUNT(*) as cnt, SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as ok FROM flush_log WHERE timestamp >= ? GROUP BY provider',
				(since,),
			)
			typer.echo('Provider health:')
			for row in rows:
				rate = row['ok'] / row['cnt'] * 100 if row['cnt'] else 0
				typer.echo(f'  {row["provider"]}: {rate:.0f}% ({row["ok"]}/{row["cnt"]})')
		else:
			typer.echo('--- Last 30 days ---')
			typer.echo(f'Retrievals: {r.get("cnt", 0)} (avg {r.get("avg_ms", 0):.0f}ms, {r.get("avg_tokens", 0):.0f} tokens)')
			flush_cnt = f.get('cnt', 0)
			flush_ok = f.get('ok', 0)
			ratio = f'{flush_ok}/{flush_cnt}' if flush_cnt else '0/0'
			typer.echo(f'Flushes: {ratio} success (avg {f.get("avg_ms", 0):.0f}ms)')
	finally:
		await db.close()


@wiki_app.command('history')
def wiki_history(
	slug: Annotated[str, typer.Argument(help='Section slug')],
) -> None:
	asyncio.run(_wiki_history(slug))


async def _wiki_history(slug: str) -> None:
	project = load_project()
	db = await _open_project_db(project)
	try:
		rows = await db.execute_fetchall(
			'SELECT change_type, changed_at, changed_by FROM wiki_history '
			'WHERE kb_name=? AND slug=? ORDER BY id',
			(project.name, slug),
		)
		if not rows:
			typer.echo(f'No history for {slug}')
			return
		for r in rows:
			typer.echo(f'  [{r["change_type"]}] {r["changed_at"]} by {r["changed_by"] or "unknown"}')
	finally:
		await db.close()


@wiki_app.command('diff')
def wiki_diff(
	slug: Annotated[str, typer.Argument(help='Section slug')],
	v1: Annotated[int, typer.Argument(help='First version number (1-based)')],
	v2: Annotated[int, typer.Argument(help='Second version number (1-based)')],
) -> None:
	asyncio.run(_wiki_diff(slug, v1, v2))


async def _wiki_diff(slug: str, v1: int, v2: int) -> None:
	project = load_project()
	db = await _open_project_db(project)
	try:
		rows = await db.execute_fetchall(
			'SELECT content FROM wiki_history '
			'WHERE kb_name=? AND slug=? ORDER BY id LIMIT ? OFFSET ?',
			(project.name, slug, max(v1, v2), min(v1, v2) - 1),
		)
		if len(rows) < 2:
			typer.echo('Not enough versions found')
			return
		content_v1 = rows[0]['content'] if v1 < v2 else rows[1]['content']
		content_v2 = rows[1]['content'] if v1 < v2 else rows[0]['content']
		lines1 = content_v1.splitlines()
		lines2 = content_v2.splitlines()
		for _i, (l1, l2) in enumerate(zip(lines1, lines2, strict=False), 1):
			if l1 != l2:
				typer.echo(f'-{l1}' if l1 else ' ')
				typer.echo(f'+{l2}' if l2 else ' ')
		for i in range(len(lines2) - len(lines1)):
			typer.echo(f'+{lines2[len(lines1) + i]}')
	finally:
		await db.close()


@wiki_app.command('rollback')
def wiki_rollback(
	slug: Annotated[str, typer.Argument(help='Section slug')],
	to: Annotated[str | None, typer.Option('--to', help='Date (YYYY-MM-DD) or version number')] = None,
) -> None:
	asyncio.run(_wiki_rollback(slug, to))


async def _wiki_rollback(slug: str, to: str | None) -> None:
	project = load_project()
	db = await _open_project_db(project)
	try:
		if to.isdigit() if to else False:
			offset = int(to) - 1
			row = await db.execute_fetchone(
				'SELECT content FROM wiki_history WHERE kb_name=? AND slug=? ORDER BY id LIMIT 1 OFFSET ?',
				(project.name, slug, offset),
			)
			if not row:
				typer.echo(f'Version {to} not found')
				return
			content = row['content']
		else:
			row = await db.execute_fetchone(
				"SELECT content FROM wiki_history WHERE kb_name=? AND slug=? AND date(changed_at) <= ? ORDER BY id DESC LIMIT 1",
				(project.name, slug, to),
			)
			if not row:
				typer.echo(f'No version found on or before {to}')
				return
			content = row['content']
		await db.execute(
			'INSERT INTO wiki_history(kb_name, slug, content, changed_by, change_type) VALUES (?, ?, ?, ?, ?)',
			(project.name, slug, content, 'rollback', 'rollback'),
		)
		await db.execute(
			'UPDATE wiki_sections SET content=? WHERE kb_name=? AND slug=?',
			(content, project.name, slug),
		)
		await db.commit()
		typer.echo(f'Rolled back {slug} to version {to}')
	finally:
		await db.close()


@app.command('export')
def export_kb(
	format: Annotated[str, typer.Option('--format', help='toml|sqlite')] = 'toml',
	output: Annotated[str | None, typer.Option('--output')] = None,
) -> None:
	asyncio.run(_export_kb(format, output))


async def _export_kb(format: str, output: str | None) -> None:
	project = load_project()
	db = await _open_project_db(project)
	try:
		if format == 'sqlite':
			out_path = output or f'{project.name}-kb-backup.db'
			await db.execute(f"VACUUM INTO '{out_path}'")
			await db.commit()
			typer.echo(f'Exported SQLite snapshot: {out_path}')
			return

		rows = await db.execute_fetchall(
			'SELECT section, slug, content, token_count FROM wiki_sections '
			'WHERE kb_name=? AND archived=FALSE ORDER BY section, slug',
			(project.name,),
		)
		lines = [f'# imbalance KB export: {project.name}', f'# Sections: {len(rows)}', '']
		for r in rows:
			lines.append('[[section]]')
			lines.append(f'section = "{r["section"]}"')
			lines.append(f'slug = "{r["slug"]}"')
			lines.append(f'token_count = {r["token_count"]}')
			lines.append('content = """')
			lines.append(r['content'])
			lines.append('"""')
			lines.append('')
		result = '\n'.join(lines)
		if output:
			from pathlib import Path

			Path(output).write_text(result, encoding='utf-8')
			typer.echo(f'Exported to {output}')
		else:
			typer.echo(result)
	finally:
		await db.close()


@app.command('import')
def import_kb(
	path: Annotated[str, typer.Argument(help='TOML file to import')],
	merge: Annotated[bool, typer.Option('--merge/--replace')] = True,
) -> None:
	asyncio.run(_import_kb(path, merge))


async def _import_kb(path: str, merge: bool) -> None:
	import tomllib
	from pathlib import Path

	project = load_project()
	db = await _open_project_db(project)
	try:
		raw = tomllib.loads(Path(path).read_text(encoding='utf-8'))
		sections = raw.get('section', [])
		store = SQLiteStore(db, project.name)
		for s in sections:
			await store.upsert_section(
				slug=s['slug'],
				section=s['section'],
				content=s['content'],
				token_count=s.get('token_count', len(s['content'].split())),
			)
		typer.echo(f'Imported {len(sections)} sections (merge={merge})')
	finally:
		await db.close()


@app.command('consolidate')
def consolidate_memories() -> None:
	"""Consolidate raw memories into project summary via LLM."""
	asyncio.run(_consolidate_memories())


async def _consolidate_memories() -> None:
	from imbalance.core.consolidation import consolidate_raw_memories

	project = load_project()
	db = await _open_project_db(project)
	try:
		store = SQLiteStore(db, project.name)
		router = ModelRouter(openrouter_key=_get_openrouter_key())
		result = await consolidate_raw_memories(store, router)
		if result.updated:
			typer.echo(
				f'Consolidated {result.memories_consumed} memories '
				f'({len(result.summary.split()) if result.summary else 0} tokens)'
			)
		else:
			typer.echo('No unconsumed raw memories to consolidate')
	finally:
		await db.close()


@app.command('scan')
def scan_code(
	directory: Annotated[str, typer.Argument(help='Directory to scan')] = '.',
	extract: Annotated[
		str | None, typer.Option('--extract', help='Filter: decisions|patterns|issues|notes')
	] = None,
	watch: Annotated[bool, typer.Option('--watch', help='Watch mode: re-scan on file changes')] = False,
) -> None:
	"""Scan codebase for IMBALANCE: markers and import into KB."""
	from imbalance.core.scanner import scan_directory

	root = Path(directory).resolve()
	if watch:
		import time
		typer.echo('Watching for changes... (Ctrl+C to stop)')
		hashes: dict[Path, float] = {}
		try:
			while True:
				time.sleep(2)
				hits = scan_directory(root)
				if extract:
					hits = [h for h in hits if h.section == extract]
				for hit in hits:
					mtime = hit.file.stat().st_mtime
					if hashes.get(hit.file) != mtime:
						hashes[hit.file] = mtime
						typer.echo(f'{hit.file.relative_to(root)}:{hit.line} [{hit.marker_type}] {hit.content}')
		except KeyboardInterrupt:
			typer.echo('\nStopped watching')
			return
	hits = scan_directory(root)
	if extract:
		hits = [h for h in hits if h.section == extract]
	if not hits:
		typer.echo('No IMBALANCE markers found')
		return
	for hit in hits:
		typer.echo(f'{hit.file.relative_to(root)}:{hit.line} [{hit.marker_type}] {hit.content}')
	typer.echo(f'\n{len(hits)} markers found')


@app.command('notify')
def notify_test() -> None:
	"""Test system notifications."""
	from imbalance.core.notifications import send_system_notification

	ok = send_system_notification('imbalance', 'Notifications are working!')
	typer.echo(f'Notification sent: {ok}')


@app.command('eval')
def eval_retrieval(
	query: Annotated[str, typer.Argument(help='Test query')],
	expected: Annotated[
		str | None, typer.Option('--expected', help='Comma-separated expected slugs')
	] = None,
	scope: Annotated[str | None, typer.Option('--scope')] = None,
) -> None:
	"""Evaluate retrieval quality for a query."""
	asyncio.run(_eval_retrieval(query, expected, scope))


async def _eval_retrieval(
	query: str, expected: str | None, scope: str | None
) -> None:
	from imbalance.core.eval import EvalQuery, run_eval

	project = load_project()
	db = await _open_project_db(project)
	try:
		store = SQLiteStore(db, project.name)
		engine = QueryEngine(store, cache_ttl=0, confidence_weight=project.config.confidence_weight)
		expected_slugs = [s.strip() for s in expected.split(',')] if expected else []
		scope_list = [s.strip() for s in scope.split(',')] if scope else None
		eq = EvalQuery(query=query, expected_slugs=expected_slugs, scope=scope_list)
		report = await run_eval([eq], engine)
		typer.echo(report.format_summary())
	finally:
		await db.close()


eval_app = typer.Typer(help='Evaluation commands.')
app.add_typer(eval_app, name='eval')


@eval_app.command('run')
def eval_run(
	file: Annotated[str | None, typer.Option('--file', help='JSON file with eval queries')] = None,
) -> None:
	"""Run eval from ground truth or file."""
	asyncio.run(_eval_run(file))


async def _eval_run(file: str | None) -> None:
	from imbalance.core.eval import EvalQuery, run_eval

	project = load_project()
	db = await _open_project_db(project)
	try:
		store = SQLiteStore(db, project.name)
		engine = QueryEngine(store, cache_ttl=0, confidence_weight=project.config.confidence_weight)

		if file:
			import json
			queries = [EvalQuery(**q) for q in json.loads(Path(file).read_text())]
		else:
			rows = await db.execute_fetchall(
				'SELECT query, expected_slugs FROM eval_ground_truth WHERE kb_name=?',
				(project.name,),
			)
			queries = [
				EvalQuery(query=r['query'], expected_slugs=json.loads(r['expected_slugs']))
				for r in rows
			]
		if not queries:
			typer.echo('No queries to evaluate')
			return
		report = await run_eval(queries, engine)
		typer.echo(report.format_summary())
	finally:
		await db.close()


@eval_app.command('record')
def eval_record(
	session: Annotated[str, typer.Option('--session', help='Session ID to record queries from')],
) -> None:
	"""Record queries from a session as ground truth."""
	asyncio.run(_eval_record(session))


async def _eval_record(session: str) -> None:
	import json


	project = load_project()
	db = await _open_project_db(project)
	try:
		rows = await db.execute_fetchall(
			'SELECT query, returned_slugs FROM retrieval_log WHERE session_id=?',
			(session,),
		)
		if not rows:
			typer.echo(f'No retrieval log entries found for session {session}')
			return
		for r in rows:
			expected = r['returned_slugs'].split(',') if r['returned_slugs'] else []
			await db.execute(
				'INSERT OR REPLACE INTO eval_ground_truth(kb_name, query, expected_slugs, source_session) VALUES (?, ?, ?, ?)',
				(project.name, r['query'], json.dumps(expected), session),
			)
		await db.commit()
		typer.echo(f'Recorded {len(rows)} queries from session {session}')
	finally:
		await db.close()


@eval_app.command('compare')
def eval_compare(
	config1: Annotated[str, typer.Argument(help='First config name')],
	config2: Annotated[str, typer.Argument(help='Second config name')],
) -> None:
	"""Compare two retrieval configs."""
	typer.echo('A/B comparison coming soon')


if __name__ == '__main__':
	app()
