CREATE TABLE IF NOT EXISTS code_symbols (
	id INTEGER PRIMARY KEY,
	kb_name TEXT NOT NULL,
	name TEXT NOT NULL,
	kind TEXT NOT NULL,
	file_path TEXT NOT NULL,
	line INTEGER NOT NULL,
	end_line INTEGER NOT NULL,
	signature TEXT NOT NULL,
	language TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_code_symbols_name
	ON code_symbols(kb_name, name);

CREATE INDEX IF NOT EXISTS idx_code_symbols_file
	ON code_symbols(kb_name, file_path);

CREATE TABLE IF NOT EXISTS trigram_index (
	trigram TEXT NOT NULL,
	rowid INTEGER NOT NULL REFERENCES code_symbols(id),
	UNIQUE(trigram, rowid)
);

CREATE INDEX IF NOT EXISTS idx_trigram_lookup
	ON trigram_index(trigram, rowid);