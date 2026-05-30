from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from imbalance.core.project import load_project
from imbalance.storage.db import open_db, run_migrations

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/ui')

TEMPLATES_DIR = Path(__file__).parent.parent / 'templates'
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


async def _get_db():
	project = load_project()
	db = await open_db(project.db_path)
	await run_migrations(db)
	return db, project


@router.get('/', response_class=HTMLResponse)
async def index(request: Request):
	return HTMLResponse(templates.TemplateResponse('pages/dashboard.html', {'request': request}))


@router.get('/dashboard', response_class=HTMLResponse)
async def dashboard(request: Request):
	db, project = await _get_db()
	try:
		wiki = await db.execute_fetchall(
			'SELECT COUNT(*) as cnt FROM wiki_sections WHERE kb_name=? AND archived=FALSE',
			(project.name,),
		)
		sessions = await db.execute_fetchall(
			'SELECT COUNT(*) as cnt FROM sessions WHERE kb_name=?',
			(project.name,),
		)
		queue = await db.execute_fetchall('SELECT COUNT(*) as cnt FROM flush_queue')
		tokens = await db.execute_fetchall(
			'SELECT COALESCE(SUM(token_count), 0) as total FROM wiki_sections WHERE kb_name=? AND archived=FALSE',
			(project.name,),
		)

		return HTMLResponse(templates.TemplateResponse('pages/dashboard.html', {
			'request': request,
			'wiki_count': wiki[0]['cnt'] if wiki else 0,
			'session_count': sessions[0]['cnt'] if sessions else 0,
			'queue_count': queue[0]['cnt'] if queue else 0,
			'token_count': tokens[0]['total'] if tokens else 0,
		}))
	finally:
		await db.close()


@router.get('/wiki', response_class=HTMLResponse)
async def wiki(request: Request):
	return HTMLResponse(templates.TemplateResponse('pages/wiki.html', {'request': request}))


@router.get('/wiki/{slug}', response_class=HTMLResponse)
async def wiki_detail(request: Request, slug: str):
	db, project = await _get_db()
	try:
		rows = await db.execute_fetchall(
			'SELECT * FROM wiki_sections WHERE kb_name=? AND slug=?',
			(project.name, slug),
		)
		if not rows:
			raise HTTPException(status_code=404, detail='Section not found')

		section = dict(rows[0])
		return HTMLResponse(templates.TemplateResponse('pages/wiki_detail.html', {
			'request': request,
			'section': section,
		}))
	finally:
		await db.close()


@router.get('/search', response_class=HTMLResponse)
async def search(request: Request):
	return HTMLResponse(templates.TemplateResponse('pages/search.html', {'request': request}))


@router.get('/sessions', response_class=HTMLResponse)
async def sessions(request: Request):
	return HTMLResponse(templates.TemplateResponse('pages/sessions.html', {'request': request}))


@router.get('/queue', response_class=HTMLResponse)
async def queue(request: Request):
	return HTMLResponse(templates.TemplateResponse('pages/queue.html', {'request': request}))
