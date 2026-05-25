import json

import pytest
from imbalance.core.session import SessionStatus, FlushPayload


def test_session_status_values():
	assert SessionStatus.ACTIVE == "active"
	assert SessionStatus.PENDING_FLUSH == "pending_flush"
	assert SessionStatus.FLUSHED == "flushed"
	assert SessionStatus.FAILED == "failed"


def test_flush_payload_from_json():
	payload = FlushPayload.from_json('{"summary": "test", "decisions": ["a"], "next_steps": ["b"]}')
	assert payload.summary == "test"
	assert payload.decisions == ["a"]
	assert payload.next_steps == ["b"]


def test_flush_payload_from_json_defaults():
	payload = FlushPayload.from_json('{"summary": "test"}')
	assert payload.summary == "test"
	assert payload.decisions == []
	assert payload.next_steps == []


def test_flush_payload_from_json_invalid():
	with pytest.raises(Exception):
		FlushPayload.from_json('not json')