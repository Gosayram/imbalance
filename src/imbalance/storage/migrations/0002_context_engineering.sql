CREATE TABLE IF NOT EXISTS memory_summary (
	kb_name TEXT PRIMARY KEY,
	content TEXT NOT NULL,
	token_count INTEGER NOT NULL,
	updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS rollout_summaries (
	id TEXT PRIMARY KEY,
	kb_name TEXT NOT NULL,
	session_id TEXT NOT NULL REFERENCES sessions(id),
	content TEXT NOT NULL,
	token_count INTEGER NOT NULL,
	created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS raw_memories (
	id INTEGER PRIMARY KEY,
	kb_name TEXT NOT NULL,
	session_id TEXT NOT NULL,
	memory_type TEXT NOT NULL,
	content TEXT NOT NULL,
	confidence REAL NOT NULL DEFAULT 0.5,
	consumed BOOLEAN NOT NULL DEFAULT FALSE,
	created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
	CHECK(memory_type IN ('decision', 'workflow', 'constraint', 'preference', 'issue'))
);

CREATE TABLE IF NOT EXISTS tool_result_receipts (
	id TEXT PRIMARY KEY,
	session_id TEXT NOT NULL,
	tool_name TEXT NOT NULL,
	content_hash TEXT NOT NULL,
	preview TEXT NOT NULL,
	bytes INTEGER NOT NULL,
	ref_path TEXT,
	created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_raw_memories_unconsumed
	ON raw_memories(kb_name, consumed, created_at)
	WHERE consumed = FALSE;

CREATE INDEX IF NOT EXISTS idx_rollout_summaries_session
	ON rollout_summaries(kb_name, session_id);
