from __future__ import annotations

import logging
from typing import Any

import aiosqlite
import mcp.server.stdio
import mcp.types as types
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.notification import NotificationOptions

from imbalance.core.project import Project, load_project
from imbalance.core.query import QueryEngine
from imbalance.core.write import WriteEngine
from imbalance.storage.db import open_db, run_migrations
from imbalance.storage.store import SQLiteStore

logger = logging.getLogger(__name__)

server = Server('imbalance')


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
	return [
		types.Tool(
			name='get_context',
			description='Retrieve relevant context from the knowledge base',
			inputSchema={
				'type': 'object',
				'properties': {
					'query': {'type': 'string', 'description': 'Search query'},
					'budget_tokens': {'type': 'integer', 'default': 2000},
					'scope': {'type': 'array', 'items': {'type': 'string'}},
					'session_id': {'type': 'string'},
				},
				'required': ['query'],
			},
		),
		types.Tool(
			name='save_fact',
			description='Save a fact or decision to the knowledge base',
			inputSchema={
				'type': 'object',
				'properties': {
					'content': {'type': 'string', 'description': 'Content to save'},
					'section': {'type': 'string', 'default': 'context'},
					'slug': {'type': 'string'},
					'tags': {'type': 'array', 'items': {'type': 'string'}},
					'session_id': {'type': 'string'},
				},
				'required': ['content'],
			},
		),
		types.Tool(
			name='flush_session',
			description='Flush session summary to knowledge base',
			inputSchema={
				'type': 'object',
				'properties': {
					'session_id': {'type': 'string'},
					'summary': {'type': 'string'},
					'decisions': {'type': 'array', 'items': {'type': 'string'}},
					'next_steps': {'type': 'array', 'items': {'type': 'string'}},
				},
				'required': ['session_id', 'summary'],
			},
		),
		types.Tool(
			name='get_status',
			description='Get current KB status and stats',
			inputSchema={'type': 'object', 'properties': {}},
		),
		types.Tool(
			name='list_topics',
			description='List all topics/sections in the KB',
			inputSchema={'type': 'object', 'properties': {}},
		),
		types.Tool(
			name='resume_session',
			description='Resume a pending session after crash',
			inputSchema={
				'type': 'object',
				'properties': {
					'session_id': {'type': 'string', 'description': 'Session UUID to resume'},
				},
				'required': ['session_id'],
			},
		),
		types.Tool(
			name='report_context_usage',
			description='Report context window usage and get budget action recommendation',
			inputSchema={
				'type': 'object',
				'properties': {
					'used_tokens': {'type': 'integer', 'description': 'Tokens currently used'},
					'total_tokens': {'type': 'integer', 'description': 'Total context window size'},
					'session_id': {'type': 'string'},
				},
				'required': ['used_tokens', 'total_tokens'],
			},
		),
		types.Tool(
			name='save_compaction_summary',
			description='Save session state BEFORE compaction so it can be restored after',
			inputSchema={
				'type': 'object',
				'properties': {
					'session_id': {'type': 'string'},
					'summary': {'type': 'string', 'description': 'Current session summary'},
					'decisions': {'type': 'array', 'items': {'type': 'string'}},
					'findings': {'type': 'array', 'items': {'type': 'string'}},
					'next_steps': {'type': 'array', 'items': {'type': 'string'}},
				},
				'required': ['session_id', 'summary'],
			},
		),
	]


@server.call_tool()
async def handle_call_tool(
	name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
	if arguments is None:
		arguments = {}

	project = load_project()
	db = await open_db(project.db_path)
	await run_migrations(db)
	store = SQLiteStore(db, project.name)

	try:
		if name == 'get_context':
			return await _get_context(store, arguments)
		if name == 'save_fact':
			return await _save_fact(store, arguments)
		if name == 'flush_session':
			return await _flush_session(db, project, arguments)
		if name == 'get_status':
			return await _get_status(db, project.name)
		if name == 'list_topics':
			return await _list_topics(db, project.name)
		if name == 'resume_session':
			return await _resume_session(db, project, arguments)
		if name == 'report_context_usage':
			return await _report_context_usage(arguments)
		if name == 'save_compaction_summary':
			return await _save_compaction_summary(db, project, arguments)
		raise ValueError(f'Unknown tool: {name}')
	finally:
		await db.close()


async def _get_context(store: SQLiteStore, args: dict[str, Any]) -> list[types.TextContent]:
	query = args.get('query', '')
	budget = args.get('budget_tokens', 2000)
	scope = args.get('scope')
	session_id = args.get('session_id')

	pack = await QueryEngine(store).get_context_pack(
		query=query,
		budget_tokens=budget,
		scope=scope,
		session_id=session_id,
	)
	return [types.TextContent(type='text', text=pack.render_markdown())]


async def _save_fact(store: SQLiteStore, args: dict[str, Any]) -> list[types.TextContent]:
	result = await WriteEngine(store).save_fact(
		content=args.get('content', ''),
		section=args.get('section', 'context'),
		slug=args.get('slug'),
		tags=args.get('tags', []),
		session_id=args.get('session_id'),
	)
	return [
		types.TextContent(type='text', text=f'Saved {result.slug} ({result.token_count} tokens)')
	]


async def _flush_session(
	db: aiosqlite.Connection, project: Project, args: dict[str, Any]
) -> list[types.TextContent]:
	from imbalance.core.session import FlushPayload, SessionManager

	manager = SessionManager(db=db, kb_name=project.name, pending_dir=project.kb_dir / 'pending')
	payload = FlushPayload(
		summary=args.get('summary', ''),
		decisions=args.get('decisions', []),
		next_steps=args.get('next_steps', []),
	)
	path = await manager.prepare_flush(args['session_id'], payload)
	await manager.enqueue_pending(args['session_id'])
	return [types.TextContent(type='text', text=f'Checkpointed {args["session_id"]}: {path}')]


async def _get_status(db: Any, kb_name: str) -> list[types.TextContent]:
	from imbalance.core.queue import FlushQueue

	queue = FlushQueue(db)
	queue_count = await queue.count()
	sessions = await db.execute_fetchall(
		'SELECT COUNT(*) as cnt FROM sessions WHERE kb_name=?', (kb_name,)
	)
	session_count = sessions[0]['cnt'] if sessions else 0
	wiki_count = await db.execute_fetchall(
		'SELECT COUNT(*) as cnt FROM wiki_sections WHERE kb_name=? AND archived=FALSE', (kb_name,)
	)
	wiki_rows = wiki_count[0]['cnt'] if wiki_count else 0

	return [
		types.TextContent(
			type='text',
			text=f'Sessions: {session_count}\nWiki sections: {wiki_rows}\nPending queue: {queue_count}',
		)
	]


async def _list_topics(db: Any, kb_name: str) -> list[types.TextContent]:
	rows = await db.execute_fetchall(
		'SELECT section, slug FROM wiki_sections WHERE kb_name=? AND archived=FALSE ORDER BY section, slug',
		(kb_name,),
	)
	topics = [f'{r["section"]}/{r["slug"]}' for r in rows]
	return [types.TextContent(type='text', text='\n'.join(topics) if topics else 'No topics found')]


async def _resume_session(
	db: Any, project: Project, arguments: dict[str, Any]
) -> list[types.TextContent]:
	from imbalance.core.session import SessionManager, SessionStatus

	session_id = arguments.get('session_id')
	if not session_id:
		raise ValueError('session_id required')

	manager = SessionManager(db=db, kb_name=project.name, pending_dir=project.kb_dir / 'pending')
	session = await manager.get(session_id)
	if session is None:
		raise ValueError(f'Unknown session: {session_id}')

	if session.status == SessionStatus.ACTIVE:
		return [types.TextContent(type='text', text=f'Session {session_id} already active')]

	await db.execute(
		"UPDATE sessions SET status=? WHERE id=?",
		(SessionStatus.ACTIVE.value, session_id),
	)
	await db.commit()
	return [types.TextContent(type='text', text=f'Resumed session {session_id}')]


async def _report_context_usage(arguments: dict[str, Any]) -> list[types.TextContent]:
	from imbalance.core.budget import SessionBudgetMonitor

	monitor = SessionBudgetMonitor()
	action = monitor.check(
		used_tokens=arguments.get('used_tokens', 0),
		total_tokens=arguments.get('total_tokens', 1),
	)
	return [types.TextContent(type='text', text=action.message if action.message else action.action)]


async def _save_compaction_summary(
	db: Any, project: Project, arguments: dict[str, Any]
) -> list[types.TextContent]:
	session_id = arguments.get('session_id')
	if not session_id:
		raise ValueError('session_id required')

	summary = arguments.get('summary', '')
	decisions = arguments.get('decisions', [])
	findings = arguments.get('findings', [])
	next_steps = arguments.get('next_steps', [])

	parts = [summary]
	if decisions:
		parts.append('Decisions:\n' + '\n'.join('- ' + d for d in decisions))
	if findings:
		parts.append('Findings:\n' + '\n'.join('- ' + f for f in findings))
	if next_steps:
		parts.append('Next steps:\n' + '\n'.join('- ' + s for s in next_steps))
	content = '\n\n'.join(parts)

	slug = 'context/compaction-' + session_id[:8]
	await db.execute(
		"""INSERT INTO wiki_sections
			(kb_name, section, slug, content, token_count, session_id, compaction_point)
		VALUES (?, 'context', ?, ?, ?, ?, TRUE)
		ON CONFLICT(kb_name, slug) DO UPDATE SET
			content = excluded.content,
			token_count = excluded.token_count,
			session_id = excluded.session_id,
			updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now'),
			compaction_point = TRUE""",
		(project.name, slug, content, len(content.split()), session_id),
	)
	await db.execute(
		"UPDATE sessions SET compacted_at=strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE id=?",
		(session_id,),
	)
	await db.commit()

	return [
		types.TextContent(
			type='text',
			text=(
				'Compaction summary saved to KB. '
				'After compaction completes, call get_context("current session state") '
				'to restore context into the new window.'
			),
		)
	]


async def main() -> None:
	async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
		await server.run(
			read_stream,
			write_stream,
			InitializationOptions(
				server_name='imbalance',
				server_version='0.1.0',
				capabilities=server.get_capabilities(
					notification_options=NotificationOptions(),
					experimental_capabilities={},
				),
			),
		)


if __name__ == '__main__':
	import asyncio

	asyncio.run(main())
