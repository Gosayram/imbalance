import pytest
import aiosqlite
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
async def db(tmp_path):
    """In-memory SQLite with all migrations. Fast, isolated."""
    from imbalance.storage.db import open_db, run_migrations
    conn = await open_db(tmp_path / "test.db")
    await run_migrations(conn)
    yield conn
    await conn.close()


@pytest.fixture
async def db_with_data(db):
    """DB with pre-populated wiki_sections for retrieval tests."""
    sections = [
        ("test-kb", "stack",     "stack",              "Python 3.14, FastAPI 0.136, PostgreSQL 17", 42),
        ("test-kb", "decisions", "decisions/001-db",   "# ADR-001: PostgreSQL\nChose PG for JSONB.", 38),
        ("test-kb", "decisions", "decisions/002-auth", "# ADR-002: JWT\nStateless JWT, refresh in httpOnly.", 35),
        ("test-kb", "context",   "context",            "Current sprint: auth middleware refactoring.", 28),
        ("test-kb", "issues",    "issues",             "Bug: migration 0014 fails on empty DB.", 22),
    ]
    await db.executemany(
        "INSERT INTO wiki_sections(kb_name, section, slug, content, token_count) VALUES (?,?,?,?,?)",
        sections,
    )
    await db.commit()
    yield db


@pytest.fixture
def sample_project(tmp_path) -> "Project":
    """Minimal project with imbalance.toml in temp directory."""
    from imbalance.core.project import Project
    toml_content = """
[project]
name = "test-kb"
version = "1"

[kb]
store = "test-kb"

[retrieval]
budget_tokens = 2000

[flush]
auto = false
provider = "openrouter"
max_tokens = 600
"""
    toml_path = tmp_path / "imbalance.toml"
    toml_path.write_text(toml_content)
    return Project.from_toml(toml_path, data_dir=tmp_path / "data")


@pytest.fixture
def mock_router():
    """ModelRouter that never hits the network."""
    router = AsyncMock()
    router.complete.return_value = '{"decisions": [], "facts": [{"content": "test fact", "tags": ["test"]}], "issues": [], "next_steps": ["Write tests"], "current_focus": "Testing"}'
    return router


@pytest.fixture
def session_log_short() -> str:
    return (Path(__file__).parent / "fixtures/session_logs/short_session.toml").read_text()


@pytest.fixture
def session_log_long() -> str:
    return (Path(__file__).parent / "fixtures/session_logs/long_session.toml").read_text()
