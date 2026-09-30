import pytest

from app.services.query_service import (
    DatabaseUnavailableError,
    QueryExecutionError,
    QueryTimeoutError,
)
from tests.factories import raw_plan_seq_scan

ANALYZE = "/api/queries/analyze"
COMPARE = "/api/queries/compare"
MUMBAI = {"query": "SELECT * FROM users WHERE city = 'Mumbai';"}


def fail_with(error):
    def fake(db, sql):
        raise error

    return fake


@pytest.fixture
def explain_must_not_run(monkeypatch):
    def boom(db, sql):
        raise AssertionError("EXPLAIN ANALYZE must not run for rejected queries")

    monkeypatch.setattr("app.services.analysis_service.run_explain_analyze", boom)


# ---------- health ----------

def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------- analyze: success ----------

def test_analyze_returns_metrics_issues_and_recommendations(client, fake_explain):
    response = client.post(ANALYZE, json=MUMBAI)

    assert response.status_code == 200
    body = response.json()
    assert body["execution_time_ms"] == pytest.approx(1.95)
    assert body["planning_time_ms"] == pytest.approx(0.08)
    assert body["rows_returned"] == 1012
    assert body["plan"]["node_type"] == "Seq Scan"
    assert {i["rule_id"] for i in body["issues"]} == {"LARGE_SEQ_SCAN", "SEQ_SCAN_WITH_FILTER"}
    assert "CREATE INDEX idx_users_city" in body["recommendations"][0]["sql_suggestion"]


# ---------- analyze: rejected input ----------

@pytest.mark.parametrize(
    "sql, expected",
    [
        ("DELETE FROM users", "Only read-only queries are supported."),
        ("DROP TABLE users", "Only read-only queries are supported."),
        ("SELECT 1; DROP TABLE users", "single SQL statement"),
    ],
)
def test_unsafe_queries_get_400_and_never_reach_postgresql(client, explain_must_not_run, sql, expected):
    response = client.post(ANALYZE, json={"query": sql})

    assert response.status_code == 400
    assert expected in response.json()["detail"]


@pytest.mark.parametrize(
    "body",
    [{"query": ""}, {}, {"query": "SELECT " + "a" * 10_000}],
    ids=["empty", "missing-field", "too-long"],
)
def test_invalid_request_bodies_get_422(client, body):
    assert client.post(ANALYZE, json=body).status_code == 422


# ---------- analyze: database and plan problems ----------

@pytest.mark.parametrize(
    "error, status, message",
    [
        (QueryTimeoutError(), 408, "Query exceeded the allowed analysis time."),
        (DatabaseUnavailableError(), 503, "Database is unavailable."),
        (QueryExecutionError('relation "userz" does not exist'), 400, 'relation "userz" does not exist'),
    ],
)
def test_analysis_errors_become_friendly_http_errors(
    client, fake_explain, monkeypatch, error, status, message
):
    monkeypatch.setattr("app.services.analysis_service.run_explain_analyze", fail_with(error))

    response = client.post(ANALYZE, json=MUMBAI)

    assert response.status_code == status
    assert message in response.json()["detail"]
    assert "Traceback" not in response.text


def test_an_unreadable_plan_gives_a_friendly_500(client, fake_explain, monkeypatch):
    monkeypatch.setattr("app.services.analysis_service.run_explain_analyze", lambda db, sql: [])

    response = client.post(ANALYZE, json=MUMBAI)

    assert response.status_code == 500
    assert response.json()["detail"] == "Unable to read the PostgreSQL execution plan."


# ---------- compare ----------

def test_compare_runs_each_query_three_times(client, fake_explain, monkeypatch):
    calls = []

    def counting(db, sql):
        calls.append(sql)
        return raw_plan_seq_scan()

    monkeypatch.setattr("app.services.analysis_service.run_explain_analyze", counting)

    response = client.post(COMPARE, json={"before_query": "SELECT 1", "after_query": "SELECT 2"})

    assert response.status_code == 200
    body = response.json()
    assert len(calls) == 6
    assert body["runs"] == 3
    assert body["verdict"] == "no_significant_change"
    assert body["metrics"][0]["key"] == "execution_time"


def test_compare_says_which_query_was_rejected(client, fake_explain):
    first = client.post(COMPARE, json={"before_query": "DELETE FROM users", "after_query": "SELECT 1"})
    assert first.status_code == 400
    assert first.json()["detail"].startswith("Before query:")

    second = client.post(COMPARE, json={"before_query": "SELECT 1", "after_query": "DROP TABLE users"})
    assert second.status_code == 400
    assert second.json()["detail"].startswith("After query:")


# ---------- history ----------

def test_unknown_history_id_returns_404(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.history.get_analysis", lambda db, analysis_id: None)

    response = client.get("/api/history/9999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Analysis not found."


def test_empty_history_returns_an_empty_list(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.history.list_history", lambda db, limit: [])
    assert client.get("/api/history").json() == []


@pytest.mark.parametrize("limit", [0, 201])
def test_history_limit_is_validated(client, limit):
    assert client.get(f"/api/history?limit={limit}").status_code == 422


# ---------- CORS ----------

def test_the_frontend_origin_is_allowed(client):
    response = client.options(
        ANALYZE,
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_other_origins_are_not_allowed(client):
    response = client.options(
        ANALYZE,
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in response.headers
