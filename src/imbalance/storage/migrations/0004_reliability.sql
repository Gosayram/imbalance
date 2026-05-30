-- Clean up duplicate entries, keeping only the oldest per session
DELETE FROM flush_queue WHERE id NOT IN (
	SELECT MIN(id) FROM flush_queue GROUP BY session_id
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_flush_queue_session
	ON flush_queue(session_id);

CREATE INDEX IF NOT EXISTS idx_flush_queue_due
	ON flush_queue(next_retry, id);