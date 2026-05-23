from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from imbalance.core.project import load_project
from imbalance.core.query import QueryEngine
from imbalance.storage.db import open_db, run_migrations
from imbalance.storage.store import SQLiteStore

logger = logging.getLogger(__name__)

MAX_BUDGET_TOKENS = 100000


def create_app() -> FastAPI:
	app = FastAPI(
		title='imbalance',
		version='0.1.0',
	)

	app.add_middleware(
		CORSMiddleware,
		allow_origins=['http://localhost:3000', 'http://localhost:5173'],
		allow_credentials=True,
		allow_methods=['*'],
		allow_headers=['*'],
	)

	@app.get('/health')
	async def health() -> dict[str, str]:
		return {'status': 'ok'}

	@app.get('/status')
	async def status() -> dict[str, object]:
		project = load_project()
		db = await open_db(project.db_path)
		await run_migrations(db)

		try:
			cursor = await db.execute_fetchall(
				'SELECT COUNT(*) as cnt FROM sessions WHERE kb_name=?',
				(project.name,),
			)
			sessions = cursor[0]['cnt'] if cursor else 0

			cursor = await db.execute_fetchall(
				'SELECT COUNT(*) as cnt FROM wiki_sections WHERE kb_name=? AND archived=FALSE',
				(project.name,),
			)
			wiki = cursor[0]['cnt'] if cursor else 0

			cursor = await db.execute_fetchall('SELECT COUNT(*) as cnt FROM flush_queue')
			queue = cursor[0]['cnt'] if cursor else 0

			return {
				'kb': project.name,
				'sessions': sessions,
				'wiki_sections': wiki,
				'pending_queue': queue,
			}
		finally:
			await db.close()

	@app.get('/context')
	async def get_context(
		query: str,
		budget_tokens: int = 2000,
	) -> dict[str, object]:
		if not query.strip():
			raise HTTPException(status_code=400, detail='Query cannot be empty')
		if budget_tokens < 1:
			raise HTTPException(status_code=400, detail='budget_tokens must be at least 1')
		if budget_tokens > MAX_BUDGET_TOKENS:
			raise HTTPException(
				status_code=400, detail=f'budget_tokens must be at most {MAX_BUDGET_TOKENS}'
			)

		project = load_project()
		db = await open_db(project.db_path)
		await run_migrations(db)
		store = SQLiteStore(db, project.name)

		try:
			pack = await QueryEngine(store).get_context_pack(
				query=query,
				budget_tokens=budget_tokens,
			)
			return {
				'query': pack.query,
				'budget_tokens': pack.budget_tokens,
				'summary': pack.summary,
				'evidence': [
					{
						'slug': c.slug,
						'section': c.section,
						'score': c.score,
						'confidence': c.confidence,
					}
					for c in pack.evidence
				],
			}
		finally:
			await db.close()

	return app
