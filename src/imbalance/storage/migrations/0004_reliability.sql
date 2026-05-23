CREATE UNIQUE INDEX IF NOT EXISTS idx_flush_queue_session
	ON flush_queue(session_id);

CREATE INDEX IF NOT EXISTS idx_flush_queue_due
	ON flush_queue(next_retry, id);
