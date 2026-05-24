from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get('/sessions')
async def sessions_index(request: Request):
	from imbalance.core.project import load_project
	from imbalance.storage.db import open_db, run_migrations

	project = load_project()
	db = await open_db(project.db_path)
	try:
		await run_migrations(db)
		rows = await db.execute_fetchall(
			'SELECT id, status, started_at, flushed_at, compacted_at '
			'FROM sessions WHERE kb_name=? ORDER BY started_at DESC LIMIT 50',
			(project.name,),
		)
		sessions = [dict(r) for r in rows]
		return request.app.state.templates.TemplateResponse(
			'sessions/index.html', {'request': request, 'sessions': sessions}
		)
	finally:
		await db.close()
