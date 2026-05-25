import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient


TEMPLATES_DIR = Path(__file__).parent.parent.parent / "src" / "imbalance" / "api" / "templates"


def _make_app():
	from imbalance.api.app import create_app
	app = create_app()
	templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
	app.state.templates = templates
	return app


@pytest.fixture
def client():
	return TestClient(_make_app())


def test_health(client):
	response = client.get("/health")
	assert response.status_code == 200
	assert response.json() == {"status": "ok"}


def test_index(client):
	response = client.get("/")
	assert response.status_code == 200


def test_wiki_view_not_found(client):
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[])
	db.close = AsyncMock()
	with patch("imbalance.core.project.load_project") as mock_proj, \
		 patch("imbalance.storage.db.open_db", return_value=db), \
		 patch("imbalance.storage.db.run_migrations"):
		mock_proj.return_value = MagicMock(name="test", db_path="/tmp/test.db")
		response = client.get("/wiki/nonexistent")
		assert response.status_code == 404


def test_wiki_edit_not_found(client):
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[])
	db.close = AsyncMock()
	with patch("imbalance.core.project.load_project") as mock_proj, \
		 patch("imbalance.storage.db.open_db", return_value=db), \
		 patch("imbalance.storage.db.run_migrations"):
		mock_proj.return_value = MagicMock(name="test", db_path="/tmp/test.db")
		response = client.get("/wiki/nonexistent/edit")
		assert response.status_code == 404


def test_api_status(client):
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[{"cnt": 0}])
	db.close = AsyncMock()
	with patch("imbalance.core.project.load_project") as mock_proj, \
		 patch("imbalance.storage.db.open_db", return_value=db), \
		 patch("imbalance.storage.db.run_migrations"):
		mock_proj.return_value = MagicMock(name="test", db_path="/tmp/test.db")
		response = client.get("/api/status")
		assert response.status_code == 200
		data = response.json()
		assert "sessions" in data


def test_status(client):
	db = AsyncMock()
	db.execute_fetchall = AsyncMock(return_value=[{"cnt": 0}])
	db.close = AsyncMock()
	with patch("imbalance.core.project.load_project") as mock_proj, \
		 patch("imbalance.storage.db.open_db", return_value=db), \
		 patch("imbalance.storage.db.run_migrations"):
		mock_proj.return_value = MagicMock(name="test", db_path="/tmp/test.db")
		response = client.get("/status")
		assert response.status_code == 200


def test_context_empty_query(client):
	response = client.get("/context?query=")
	assert response.status_code == 400


def test_context_invalid_budget(client):
	response = client.get("/context?query=test&budget_tokens=0")
	assert response.status_code == 400


def test_context_budget_too_high(client):
	response = client.get("/context?query=test&budget_tokens=999999")
	assert response.status_code == 400


def test_create_app():
	app = _make_app()
	assert app.title == "imbalance"