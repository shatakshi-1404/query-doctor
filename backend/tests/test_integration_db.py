import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.analyzer.parser import parse_plan
from app.core.config import settings
from app.core.database import SessionLocal
from app.main import app
from app.services.query_service import (
    QueryExecutionError,
    QueryTimeoutError,
    run_explain_analyze,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        session.execute(text("SELECT 1 FROM users LIMIT 1"))
        session.rollback()
    except Exception:
        session.close()
        pytest.skip("PostgreSQL with the sample database is not available")
    yield session
    session.close()


def test_explain_returns_a_parseable_plan(db):
    raw = run_explain_analyze(db, "SELECT * FROM users WHERE city = 'Mumbai'")

    plan = parse_plan(raw)
    assert plan.execution_time_ms > 0
    assert plan.root.node_type


def test_writes_are_blocked_by_the_read_only_transaction(db):
    # This bypasses the validator on purpose: PostgreSQL itself must refuse.
    with pytest.raises(QueryExecutionError) as error:
        run_explain_analyze(db, "DELETE FROM users WHERE id = -1")
    assert "read-only" in error.value.message


def test_slow_queries_hit_the_timeout(db, monkeypatch):
    monkeypatch.setattr(settings, "query_timeout_ms", 200)
    with pytest.raises(QueryTimeoutError):
        run_explain_analyze(db, "SELECT pg_sleep(2)")


def test_postgres_errors_become_readable_messages(db):
    with pytest.raises(QueryExecutionError) as error:
        run_explain_analyze(db, "SELECT * FROM userz")
    assert "userz" in error.value.message


def test_analyze_endpoint_end_to_end(db, monkeypatch):
    monkeypatch.setattr("app.api.routes.queries.save_analysis_safely", lambda d, r: r)
    client = TestClient(app)

    response = client.post("/api/queries/analyze", json={"query": "SELECT * FROM users LIMIT 5"})

    assert response.status_code == 200
    body = response.json()
    assert body["execution_time_ms"] > 0
    assert "issues" in body and "recommendations" in body
