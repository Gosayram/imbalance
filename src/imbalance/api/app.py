from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

from imbalance.core.project import load_project
from imbalance.core.query import QueryEngine
from imbalance.storage.db import open_db, run_migrations
from imbalance.storage.store import SQLiteStore

logger = logging.getLogger(__name__)

MAX_BUDGET_TOKENS = 100000

TEMPLATES_DIR = Path(__file__).parent / 'templates'


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

	templates = Environment(
		loader=FileSystemLoader(str(TEMPLATES_DIR)),
		autoescape=True,
	)

	@app.on_event('startup')
	async def _store_templates():
		app.state.templates = templates

	from imbalance.api.routes.queue_ui import router as queue_router
	from imbalance.api.routes.sessions import router as sessions_router
	from imbalance.api.routes.wiki import router as wiki_router

	app.include_router(wiki_router)
	app.include_router(sessions_router)
	app.include_router(queue_router)

	@app.get('/', response_class=HTMLResponse)
	async def index():
		return HTMLResponse(templates.get_template('index.html').render(request=None))

	@app.get('/health')
	async def health() -> dict[str, str]:
		return {'status': 'ok'}

	@app.get('/api/status')
	async def api_status(request: Request):
		project = load_project()
		db = await open_db(project.db_path)
		try:
			await run_migrations(db)
			sessions = await db.execute_fetchall(
				'SELECT COUNT(*) as cnt FROM sessions WHERE kb_name=?', (project.name,)
			)
			wiki = await db.execute_fetchall(
				'SELECT COUNT(*) as cnt FROM wiki_sections WHERE kb_name=? AND archived=FALSE',
				(project.name,),
			)
			queue = await db.execute_fetchall('SELECT COUNT(*) as cnt FROM flush_queue')
			s_cnt = sessions[0]['cnt'] if sessions else 0
			w_cnt = wiki[0]['cnt'] if wiki else 0
			q_cnt = queue[0]['cnt'] if queue else 0

			accept = request.headers.get('accept', '')
			if 'text/html' in accept:
				t = templates.get_template('partials/status.html')
				return HTMLResponse(
					t.render(
						kb=project.name, sessions=s_cnt, wiki_sections=w_cnt, pending_queue=q_cnt
					)
				)
			return {
				'kb': project.name,
				'sessions': s_cnt,
				'wiki_sections': w_cnt,
				'pending_queue': q_cnt,
			}
		finally:
			await db.close()

	@app.get('/status')
	async def status(request: Request):
		return await api_status(request)

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
		try:
			await run_migrations(db)
			store = SQLiteStore(db, project.name)

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

	@app.get('/metrics')
	async def metrics():
		from fastapi.responses import PlainTextResponse

		from imbalance.core.metrics import get_metrics
		return PlainTextResponse(
			get_metrics().render_prometheus(),
			media_type='text/plain; version=0.0.4; charset=utf-8',
		)

	return app
