from datetime import datetime

from pydantic import BaseModel


class HistoryItem(BaseModel):
    analysis_id: int
    query_text: str
    planning_time_ms: float
    execution_time_ms: float
    rows_returned: int
    issues_count: int
    created_at: datetime
