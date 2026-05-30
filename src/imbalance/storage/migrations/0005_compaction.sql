CREATE TABLE IF NOT EXISTS kb_compaction_log (
	id INTEGER PRIMARY KEY,
	kb_name TEXT NOT NULL,
	ran_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
	sections_total INTEGER,
	sections_archived INTEGER,
	sections_updated INTEGER,
	sections_evergreen INTEGER,
	duration_sec REAL
);

CREATE INDEX IF NOT EXISTS idx_compaction_log_kb
	ON kb_compaction_log(kb_name, ran_at DESC);
