from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get('/queue')
async def queue_index(request: Request):
	from imbalance.core.project import load_project
	from imbalance.storage.db import open_db, run_migrations

	project = load_project()
	db = await open_db(project.db_path)
	try:
		await run_migrations(db)
		rows = await db.execute_fetchall(
			'SELECT id, session_id, attempts, next_retry, error '
			'FROM flush_queue ORDER BY next_retry'
		)
		items = [dict(r) for r in rows]
		return request.app.state.templates.TemplateResponse(
			'queue/index.html', {'request': request, 'items': items}
		)
	finally:
		await db.close()
