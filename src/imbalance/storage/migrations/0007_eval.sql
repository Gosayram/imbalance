CREATE TABLE IF NOT EXISTS eval_results (
	id INTEGER PRIMARY KEY,
	kb_name TEXT NOT NULL,
	query TEXT NOT NULL,
	expected_slugs TEXT NOT NULL,
	returned_slugs TEXT NOT NULL,
	latency_ms INTEGER,
	tokens_used INTEGER,
	tokens_budget INTEGER,
	run_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
	config TEXT
);

CREATE TABLE IF NOT EXISTS eval_ground_truth (
	id INTEGER PRIMARY KEY,
	kb_name TEXT NOT NULL,
	query TEXT NOT NULL,
	expected_slugs TEXT NOT NULL,
	source_session TEXT,
	created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_eval_results_kb ON eval_results(kb_name, run_at);
CREATE INDEX IF NOT EXISTS idx_eval_gt_kb ON eval_ground_truth(kb_name, query);