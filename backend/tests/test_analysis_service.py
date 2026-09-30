import pytest

from app.services.analysis_service import analyze_sql
from app.services.query_validator import InvalidQueryError
from tests.factories import raw_plan


def test_the_run_with_the_median_time_is_used(monkeypatch):
    times = iter([30.0, 10.0, 20.0])
    monkeypatch.setattr(
        "app.services.analysis_service.run_explain_analyze",
        lambda db, sql: raw_plan(next(times)),
    )

    result = analyze_sql(None, "SELECT 1", runs=3)

    assert result.execution_time_ms == 20.0


def test_a_single_run_is_the_default(monkeypatch):
    calls = []

    def fake(db, sql):
        calls.append(sql)
        return raw_plan(5.0)

    monkeypatch.setattr("app.services.analysis_service.run_explain_analyze", fake)

    analyze_sql(None, "SELECT 1")
    assert len(calls) == 1


def test_the_same_cleaned_query_is_run_every_time(monkeypatch):
    calls = []

    def fake(db, sql):
        calls.append(sql)
        return raw_plan(5.0)

    monkeypatch.setattr("app.services.analysis_service.run_explain_analyze", fake)

    result = analyze_sql(None, "  SELECT 1 ;", runs=3)

    assert calls == ["SELECT 1"] * 3
    assert result.query == "SELECT 1"


def test_unsafe_queries_never_reach_postgresql(monkeypatch):
    def boom(db, sql):
        raise AssertionError("EXPLAIN ANALYZE must not run for rejected queries")

    monkeypatch.setattr("app.services.analysis_service.run_explain_analyze", boom)

    with pytest.raises(InvalidQueryError):
        analyze_sql(None, "DROP TABLE users")
