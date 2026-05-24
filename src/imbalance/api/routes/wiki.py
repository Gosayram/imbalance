from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get('/wiki')
async def wiki_index(request: Request, include_archived: bool = False):
	from imbalance.core.project import load_project
	from imbalance.storage.db import open_db, run_migrations

	project = load_project()
	db = await open_db(project.db_path)
	try:
		await run_migrations(db)
		archived_filter = '' if include_archived else 'AND archived=FALSE'
		rows = await db.execute_fetchall(
			f'SELECT section, slug, token_count, updated_at, archived '
			f'FROM wiki_sections WHERE kb_name=? {archived_filter} ORDER BY section, slug',
			(project.name,),
		)
		sections: dict[str, list[dict]] = {}
		for r in rows:
			sec = r['section']
			sections.setdefault(sec, []).append(dict(r))
		return request.app.state.templates.TemplateResponse(
			'wiki/index.html',
			{'request': request, 'sections': sections, 'include_archived': include_archived},
		)
	finally:
		await db.close()


@router.get('/wiki/{slug:path}')
async def wiki_view(request: Request, slug: str):
	import mistune

	from imbalance.core.project import load_project
	from imbalance.storage.db import open_db, run_migrations

	project = load_project()
	db = await open_db(project.db_path)
	try:
		await run_migrations(db)
		row = await db.execute_fetchall(
			'SELECT slug, section, content, token_count, updated_at, archived '
			'FROM wiki_sections WHERE kb_name=? AND slug=?',
			(project.name, slug),
		)
		if not row:
			from fastapi import HTTPException
			raise HTTPException(status_code=404, detail='Section not found')
		r = dict(row[0])
		md = mistune.create_markdown()
		r['html_content'] = md(r['content'])
		return request.app.state.templates.TemplateResponse(
			'wiki/view.html', {'request': request, 'section': r}
		)
	finally:
		await db.close()


@router.get('/wiki/{slug:path}/edit')
async def wiki_edit_form(request: Request, slug: str):
	from imbalance.core.project import load_project
	from imbalance.storage.db import open_db, run_migrations

	project = load_project()
	db = await open_db(project.db_path)
	try:
		await run_migrations(db)
		row = await db.execute_fetchall(
			'SELECT slug, section, content FROM wiki_sections WHERE kb_name=? AND slug=?',
			(project.name, slug),
		)
		if not row:
			from fastapi import HTTPException
			raise HTTPException(status_code=404, detail='Section not found')
		return request.app.state.templates.TemplateResponse(
			'wiki/edit.html', {'request': request, 'section': dict(row[0])}
		)
	finally:
		await db.close()


@router.put('/wiki/{slug:path}')
async def wiki_update(request: Request, slug: str):
	from fastapi import HTTPException

	from imbalance.core.project import load_project
	from imbalance.core.tokens import estimate_tokens
	from imbalance.storage.db import open_db, run_migrations
	from imbalance.storage.store import SQLiteStore

	project = load_project()
	db = await open_db(project.db_path)
	try:
		await run_migrations(db)
		form = await request.form()
		content = str(form.get('content', ''))
		if not content.strip():
			raise HTTPException(status_code=400, detail='Content cannot be empty')

		store = SQLiteStore(db, project.name)
		row = await db.execute_fetchall(
			'SELECT section FROM wiki_sections WHERE kb_name=? AND slug=?',
			(project.name, slug),
		)
		if not row:
			raise HTTPException(status_code=404, detail='Section not found')

		section = row[0]['section']
		token_count = estimate_tokens(content)
		await store.upsert_section(
			slug=slug, section=section, content=content, token_count=token_count
		)
		from fastapi.responses import RedirectResponse
		return RedirectResponse(url=f'/wiki/{slug}', status_code=303)
	finally:
		await db.close()
