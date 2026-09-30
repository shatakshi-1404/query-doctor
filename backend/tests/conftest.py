import os
from pathlib import Path

# Settings() reads DATABASE_URL when the app is imported. If the developer has
# neither an environment variable nor a .env file (for example on a CI server),
# use a dummy value. Nothing connects to it unless an integration test runs.
_env_file = Path(__file__).resolve().parents[1] / ".env"
if not os.environ.get("DATABASE_URL") and not _env_file.exists():
    os.environ["DATABASE_URL"] = "postgresql+psycopg2://test:test@localhost:5432/test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from tests.factories import raw_plan_seq_scan  # noqa: E402


@pytest.fixture
def client():
    """A test client whose database dependency is replaced by a harmless stand-in."""

    def fake_get_db():
        yield None

    app.dependency_overrides[get_db] = fake_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def fake_explain(monkeypatch):
    """Pretend PostgreSQL returned a Seq Scan plan, and skip saving to history."""
    monkeypatch.setattr(
        "app.services.analysis_service.run_explain_analyze",
        lambda db, sql: raw_plan_seq_scan(),
    )
    monkeypatch.setattr(
        "app.api.routes.queries.save_analysis_safely",
        lambda db, result: result,
    )
