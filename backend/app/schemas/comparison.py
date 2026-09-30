from pydantic import BaseModel, Field

from app.schemas.analysis import AnalyzeResponse


class CompareRequest(BaseModel):
    before_query: str = Field(..., min_length=1, max_length=10000)
    after_query: str = Field(..., min_length=1, max_length=10000)


class MetricComparison(BaseModel):
    key: str
    label: str
    unit: str | None = None
    before: float
    after: float
    change_pct: float | None = None
    better: bool | None = None


class CompareResponse(BaseModel):
    before: AnalyzeResponse
    after: AnalyzeResponse
    metrics: list[MetricComparison]
    verdict: str
    summary: str
    resolved_issues: list[str]
    new_issues: list[str]
    notes: list[str]
    runs: int
