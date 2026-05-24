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
		raise ValueError(f'Unknown tool: {name}')
	finally:
		await db.close()


async def _get_context(store: SQLiteStore, args: dict[str, Any]) -> list[types.TextContent]:
	query = args.get('query', '')
	budget = args.get('budget_tokens', 2000)
	scope = args.get('scope')

	pack = await QueryEngine(store).get_context_pack(
		query=query,
		budget_tokens=budget,
		scope=scope,
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
	from imbalance.core.session import SessionManager

	session_id = arguments.get('session_id')
	if not session_id:
		raise ValueError('session_id required')

	manager = SessionManager(db=db, kb_name=project.name, pending_dir=project.kb_dir / 'pending')
	session = await manager.get(session_id)
	if session is None:
		raise ValueError(f'Unknown session: {session_id}')

	if session.status == 'active':
		return [types.TextContent(type='text', text=f'Session {session_id} already active')]

	await db.execute(
		"UPDATE sessions SET status='active' WHERE id=?",
		(session_id,),
	)
	await db.commit()
	return [types.TextContent(type='text', text=f'Resumed session {session_id}')]


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
