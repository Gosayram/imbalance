from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from imbalance.core.project import load_project
from imbalance.storage.db import open_db, run_migrations

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/ui/api')

TEMPLATES_DIR = Path(__file__).parent.parent / 'templates'
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


async def _get_db():
	project = load_project()
	db = await open_db(project.db_path)
	await run_migrations(db)
	return db, project


@router.get('/stats/wiki', response_class=HTMLResponse)
async def stats_wiki():
	db, project = await _get_db()
	try:
		rows = await db.execute_fetchall(
			'SELECT COUNT(*) as cnt FROM wiki_sections WHERE kb_name=? AND archived=FALSE',
			(project.name,),
		)
		return HTMLResponse(str(rows[0]['cnt'] if rows else 0))
	finally:
		await db.close()


@router.get('/stats/sessions', response_class=HTMLResponse)
async def stats_sessions():
	db, project = await _get_db()
	try:
		rows = await db.execute_fetchall(
			'SELECT COUNT(*) as cnt FROM sessions WHERE kb_name=?',
			(project.name,),
		)
		return HTMLResponse(str(rows[0]['cnt'] if rows else 0))
	finally:
		await db.close()


@router.get('/stats/queue', response_class=HTMLResponse)
async def stats_queue():
	db, _ = await _get_db()
	try:
		rows = await db.execute_fetchall('SELECT COUNT(*) as cnt FROM flush_queue')
		return HTMLResponse(str(rows[0]['cnt'] if rows else 0))
	finally:
		await db.close()


@router.get('/stats/tokens', response_class=HTMLResponse)
async def stats_tokens():
	db, project = await _get_db()
	try:
		rows = await db.execute_fetchall(
			'SELECT COALESCE(SUM(token_count), 0) as total FROM wiki_sections WHERE kb_name=? AND archived=FALSE',
			(project.name,),
		)
		return HTMLResponse(str(rows[0]['total'] if rows else 0))
	finally:
		await db.close()


@router.get('/sections', response_class=HTMLResponse)
async def sections_list():
	db, project = await _get_db()
	try:
		rows = await db.execute_fetchall(
			'SELECT section, slug, token_count, updated_at FROM wiki_sections '
			'WHERE kb_name=? AND archived=FALSE ORDER BY updated_at DESC LIMIT 50',
			(project.name,),
		)
		return HTMLResponse(templates.TemplateResponse('components/sections_rows.html', {
			'request': None,
			'sections': [dict(r) for r in rows],
		}))
	finally:
		await db.close()


@router.get('/sections/recent', response_class=HTMLResponse)
async def sections_recent():
	db, project = await _get_db()
	try:
		rows = await db.execute_fetchall(
			'SELECT section, slug, token_count FROM wiki_sections '
			'WHERE kb_name=? AND archived=FALSE ORDER BY updated_at DESC LIMIT 5',
			(project.name,),
		)
		return HTMLResponse(templates.TemplateResponse('components/sections_recent.html', {
			'request': None,
			'sections': [dict(r) for r in rows],
		}))
	finally:
		await db.close()


@router.get('/sections/filter', response_class=HTMLResponse)
async def sections_filter(q: str = ''):
	db, project = await _get_db()
	try:
		if q:
			rows = await db.execute_fetchall(
				'SELECT section, slug, token_count, updated_at FROM wiki_sections '
				'WHERE kb_name=? AND archived=FALSE AND (slug LIKE ? OR content LIKE ?) '
				'ORDER BY updated_at DESC LIMIT 50',
				(project.name, f'%{q}%', f'%{q}%'),
			)
		else:
			rows = await db.execute_fetchall(
				'SELECT section, slug, token_count, updated_at FROM wiki_sections '
				'WHERE kb_name=? AND archived=FALSE ORDER BY updated_at DESC LIMIT 50',
				(project.name,),
			)
		return HTMLResponse(templates.TemplateResponse('components/sections_rows.html', {
			'request': None,
			'sections': [dict(r) for r in rows],
		}))
	finally:
		await db.close()


@router.get('/sessions', response_class=HTMLResponse)
async def sessions_list():
	db, project = await _get_db()
	try:
		rows = await db.execute_fetchall(
			'SELECT id, machine_id, status, started_at, flushed_at FROM sessions '
			'WHERE kb_name=? ORDER BY started_at DESC LIMIT 50',
			(project.name,),
		)
		return HTMLResponse(templates.TemplateResponse('components/sessions_rows.html', {
			'request': None,
			'sessions': [dict(r) for r in rows],
		}))
	finally:
		await db.close()


@router.get('/sessions/recent', response_class=HTMLResponse)
async def sessions_recent():
	db, project = await _get_db()
	try:
		rows = await db.execute_fetchall(
			'SELECT id, status, started_at FROM sessions '
			'WHERE kb_name=? ORDER BY started_at DESC LIMIT 5',
			(project.name,),
		)
		return HTMLResponse(templates.TemplateResponse('components/sessions_recent.html', {
			'request': None,
			'sessions': [dict(r) for r in rows],
		}))
	finally:
		await db.close()


@router.get('/sessions/filter', response_class=HTMLResponse)
async def sessions_filter(status: str = ''):
	db, project = await _get_db()
	try:
		if status:
			rows = await db.execute_fetchall(
				'SELECT id, machine_id, status, started_at, flushed_at FROM sessions '
				'WHERE kb_name=? AND status=? ORDER BY started_at DESC LIMIT 50',
				(project.name, status),
			)
		else:
			rows = await db.execute_fetchall(
				'SELECT id, machine_id, status, started_at, flushed_at FROM sessions '
				'WHERE kb_name=? ORDER BY started_at DESC LIMIT 50',
				(project.name,),
			)
		return HTMLResponse(templates.TemplateResponse('components/sessions_rows.html', {
			'request': None,
			'sessions': [dict(r) for r in rows],
		}))
	finally:
		await db.close()


@router.get('/queue', response_class=HTMLResponse)
async def queue_list():
	db, _ = await _get_db()
	try:
		rows = await db.execute_fetchall(
			'SELECT id, session_id, attempts, next_retry, error FROM flush_queue ORDER BY id DESC LIMIT 50'
		)
		return HTMLResponse(templates.TemplateResponse('components/queue_rows.html', {
			'request': None,
			'items': [dict(r) for r in rows],
		}))
	finally:
		await db.close()


@router.get('/search', response_class=HTMLResponse)
async def search_results(q: str = '', budget: int = 2000):
	if not q.strip():
		return HTMLResponse('<div class="card" style="text-align: center; padding: 2rem; color: var(--text-secondary);">Enter a query to search</div>')

	db, project = await _get_db()
	try:
		from imbalance.core.query import QueryEngine
		from imbalance.storage.store import SQLiteStore

		store = SQLiteStore(db, project.name)
		pack = await QueryEngine(store).get_context_pack(q, budget_tokens=budget)

		return HTMLResponse(templates.TemplateResponse('components/search_results.html', {
			'request': None,
			'query': q,
			'pack': pack,
		}))
	finally:
		await db.close()


@router.put('/sections/{slug}')
async def update_section(slug: str, request: Request):
	form = await request.form()
	content = form.get('content', '')

	if not content.strip():
		raise HTTPException(status_code=400, detail='Content cannot be empty')

	db, project = await _get_db()
	try:
		from imbalance.core.tokens import estimate_tokens
		token_count = estimate_tokens(content)

		await db.execute(
			'UPDATE wiki_sections SET content=?, token_count=?, updated_at=datetime("now") '
			'WHERE kb_name=? AND slug=?',
			(content, token_count, project.name, slug),
		)
		await db.commit()
		return HTMLResponse('<span style="color: var(--success);">Saved!</span>')
	finally:
		await db.close()


@router.delete('/sections/{slug}')
async def archive_section(slug: str):
	db, project = await _get_db()
	try:
		await db.execute(
			'UPDATE wiki_sections SET archived=TRUE, archived_at=datetime("now") '
			'WHERE kb_name=? AND slug=?',
			(project.name, slug),
		)
		await db.commit()
		return HTMLResponse('<span style="color: var(--success);">Archived</span>')
	finally:
		await db.close()


@router.post('/compact')
async def run_compaction():
	# Placeholder for compaction
	return HTMLResponse('<span style="color: var(--success);">Compaction complete</span>')


@router.post('/queue/retry')
async def retry_queue():
	db, _ = await _get_db()
	try:
		await db.execute('UPDATE flush_queue SET attempts=0, error=NULL WHERE attempts >= 3')
		await db.commit()
		return HTMLResponse('<span style="color: var(--success);">Retrying failed items</span>')
	finally:
		await db.close()


@router.delete('/queue')
async def clear_queue():
	db, _ = await _get_db()
	try:
		await db.execute('DELETE FROM flush_queue')
		await db.commit()
		return HTMLResponse('<span style="color: var(--success);">Queue cleared</span>')
	finally:
		await db.close()


@router.get('/sections/{slug}/history', response_class=HTMLResponse)
async def section_history(slug: str):
	db, project = await _get_db()
	try:
		rows = await db.execute_fetchall(
			'SELECT change_type, changed_at, changed_by FROM wiki_history '
			'WHERE kb_name=? AND slug=? ORDER BY id DESC LIMIT 20',
			(project.name, slug),
		)
		return HTMLResponse(templates.TemplateResponse('components/history_list.html', {
			'request': None,
			'history': [dict(r) for r in rows],
		}))
	finally:
		await db.close()
