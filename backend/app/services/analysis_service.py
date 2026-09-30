from dataclasses import asdict

from sqlalchemy.orm import Session

from app.analyzer.engine import run_rules
from app.analyzer.parser import ParsedPlan, parse_plan
from app.analyzer.recommendations import build_recommendations
from app.schemas.analysis import AnalyzeResponse
from app.services.query_service import run_explain_analyze
from app.services.query_validator import validate_read_only_query


def analyze_sql(db: Session, sql: str, runs: int = 1) -> AnalyzeResponse:
    """
    Validate, run EXPLAIN ANALYZE, parse, apply rules, build recommendations.
    With runs > 1 the query is executed several times and the run with the
    median execution time is used. Nothing is saved here.
    """
    cleaned_query = validate_read_only_query(sql)

    parsed_runs: list[ParsedPlan] = []
    for _ in range(runs):
        raw_plan = run_explain_analyze(db, cleaned_query)
        parsed_runs.append(parse_plan(raw_plan))

    parsed_runs.sort(key=lambda p: p.execution_time_ms)
    parsed = parsed_runs[len(parsed_runs) // 2]  # the median run

    issues = run_rules(parsed)
    recommendations = build_recommendations(issues)

    return AnalyzeResponse(
        query=cleaned_query,
        planning_time_ms=parsed.planning_time_ms,
        execution_time_ms=parsed.execution_time_ms,
        rows_returned=parsed.rows_returned,
        plan=asdict(parsed.root),
        issues=[asdict(issue) for issue in issues],
        recommendations=[asdict(rec) for rec in recommendations],
    )
