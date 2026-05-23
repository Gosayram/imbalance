CREATE TABLE IF NOT EXISTS wiki_history (
	id INTEGER PRIMARY KEY,
	slug TEXT NOT NULL,
	kb_name TEXT NOT NULL,
	content TEXT NOT NULL,
	changed_by TEXT,
	changed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
	change_type TEXT NOT NULL,
	CHECK(change_type IN ('create', 'update', 'archive', 'merge', 'rollback'))
);

CREATE TABLE IF NOT EXISTS kb_links (
	source_slug TEXT NOT NULL,
	target_slug TEXT NOT NULL,
	link_type TEXT NOT NULL,
	created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
	PRIMARY KEY (source_slug, target_slug, link_type)
);

CREATE TABLE IF NOT EXISTS wiki_tags (
	section_id INTEGER NOT NULL REFERENCES wiki_sections(id) ON DELETE CASCADE,
	tag TEXT NOT NULL,
	PRIMARY KEY (section_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_wiki_history_slug
	ON wiki_history(kb_name, slug, changed_at);

CREATE INDEX IF NOT EXISTS idx_wiki_tags_tag
	ON wiki_tags(tag);
