from datetime import datetime
from typing import Any

from pydantic import BaseModel


class PlanNodeOut(BaseModel):
    node_type: str
    relation_name: str | None = None
    index_name: str | None = None
    filter_condition: str | None = None
    plan_rows: int
    actual_rows: int
    actual_loops: int
    actual_total_time: float
    total_time_ms: float
    rows_removed_by_filter: int
    shared_hit_blocks: int
    shared_read_blocks: int
    children: list["PlanNodeOut"] = []


class IssueOut(BaseModel):
    rule_id: str
    title: str
    severity: str
    node_type: str
    relation_name: str | None = None
    what_happened: str
    why_it_matters: str
    what_to_investigate: str
    metrics: dict[str, Any] = {}


class RecommendationOut(BaseModel):
    title: str
    description: str
    sql_suggestion: str | None = None
    relation_name: str | None = None
    related_rule_ids: list[str] = []


class AnalyzeResponse(BaseModel):
    query: str
    planning_time_ms: float
    execution_time_ms: float
    rows_returned: int
    plan: PlanNodeOut
    issues: list[IssueOut]
    recommendations: list[RecommendationOut]
    analysis_id: int | None = None
    created_at: datetime | None = None
