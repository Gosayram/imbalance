import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from imbalance.api.app import create_app, MAX_BUDGET_TOKENS


@pytest.fixture
def client():
	return TestClient(create_app())


def test_health(client):
	response = client.get("/health")
	assert response.status_code == 200
	assert response.json() == {"status": "ok"}


def test_max_budget_tokens():
	assert MAX_BUDGET_TOKENS == 100000


@patch("imbalance.api.app.load_project")
def test_api_status_error(mock_load, client):
	mock_load.side_effect = FileNotFoundError("test")
	with pytest.raises(FileNotFoundError):
		client.get("/api/status")
