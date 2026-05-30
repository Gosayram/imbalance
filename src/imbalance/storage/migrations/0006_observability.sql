CREATE TABLE IF NOT EXISTS retrieval_log (
	id INTEGER PRIMARY KEY,
	session_id TEXT,
	query TEXT NOT NULL,
	scope TEXT,
	results_count INTEGER,
	tokens_returned INTEGER,
	tokens_budget INTEGER,
	latency_ms INTEGER,
	source TEXT,
	timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS flush_log (
	id INTEGER PRIMARY KEY,
	session_id TEXT,
	provider TEXT,
	attempt INTEGER,
	success INTEGER NOT NULL DEFAULT 0,
	latency_ms INTEGER,
	tokens_prompt INTEGER,
	tokens_response INTEGER,
	error TEXT,
	timestamp TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_retrieval_log_ts
	ON retrieval_log(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_flush_log_ts
	ON flush_log(timestamp DESC);
