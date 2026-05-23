CREATE TABLE IF NOT EXISTS wiki_sections (
	id INTEGER PRIMARY KEY,
	kb_name TEXT NOT NULL,
	section TEXT NOT NULL,
	slug TEXT NOT NULL,
	content TEXT NOT NULL,
	token_count INTEGER NOT NULL,
	session_id TEXT,
	machine_id TEXT,
	confirmation_count INTEGER NOT NULL DEFAULT 1,
	last_confirmed_at TEXT,
	archived BOOLEAN NOT NULL DEFAULT FALSE,
	archived_at TEXT,
	archive_reason TEXT,
	evergreen BOOLEAN NOT NULL DEFAULT FALSE,
	compaction_point BOOLEAN NOT NULL DEFAULT FALSE,
	updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
	UNIQUE(kb_name, slug)
);

CREATE VIRTUAL TABLE IF NOT EXISTS wiki_fts USING fts5(
	slug,
	content,
	content='wiki_sections',
	content_rowid='id',
	tokenize='unicode61'
);

CREATE TRIGGER IF NOT EXISTS wiki_ai AFTER INSERT ON wiki_sections BEGIN
	INSERT INTO wiki_fts(rowid, slug, content) VALUES (new.id, new.slug, new.content);
END;

CREATE TRIGGER IF NOT EXISTS wiki_au AFTER UPDATE ON wiki_sections BEGIN
	INSERT INTO wiki_fts(wiki_fts, rowid, slug, content)
		VALUES('delete', old.id, old.slug, old.content);
	INSERT INTO wiki_fts(rowid, slug, content) VALUES (new.id, new.slug, new.content);
END;

CREATE TRIGGER IF NOT EXISTS wiki_ad AFTER DELETE ON wiki_sections BEGIN
	INSERT INTO wiki_fts(wiki_fts, rowid, slug, content)
		VALUES('delete', old.id, old.slug, old.content);
END;

CREATE TABLE IF NOT EXISTS sessions (
	id TEXT PRIMARY KEY,
	kb_name TEXT NOT NULL,
	machine_id TEXT NOT NULL,
	status TEXT NOT NULL DEFAULT 'active',
	started_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
	flushed_at TEXT,
	compacted_at TEXT,
	log_path TEXT,
	CHECK(status IN ('active', 'pending_flush', 'flushed', 'failed'))
);

CREATE TABLE IF NOT EXISTS flush_queue (
	id INTEGER PRIMARY KEY,
	session_id TEXT NOT NULL REFERENCES sessions(id),
	payload TEXT NOT NULL,
	attempts INTEGER NOT NULL DEFAULT 0,
	next_retry TEXT,
	error TEXT,
	created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS kb_meta (
	key TEXT PRIMARY KEY,
	value TEXT NOT NULL
);

INSERT OR IGNORE INTO kb_meta VALUES ('schema_version', '1');
INSERT OR IGNORE INTO kb_meta VALUES ('created_at', strftime('%Y-%m-%dT%H:%M:%SZ','now'));

CREATE INDEX IF NOT EXISTS idx_wiki_active
	ON wiki_sections(kb_name, archived)
	WHERE archived = FALSE;

CREATE INDEX IF NOT EXISTS idx_sessions_status
	ON sessions(kb_name, status);
