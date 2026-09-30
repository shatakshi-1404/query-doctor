from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)
