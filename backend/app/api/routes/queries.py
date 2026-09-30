from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.errors import analysis_errors
from app.core.database import get_db
from app.schemas.analysis import AnalyzeResponse
from app.schemas.comparison import CompareRequest, CompareResponse
from app.schemas.query import AnalyzeRequest
from app.services.analysis_service import analyze_sql
from app.services.comparison_service import compare_analyses
from app.services.history_service import save_analysis_safely

COMPARE_RUNS = 3

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_query(payload: AnalyzeRequest, db: Session = Depends(get_db)):
    with analysis_errors():
        result = analyze_sql(db, payload.query)
    return save_analysis_safely(db, result)


@router.post("/compare", response_model=CompareResponse)
def compare_queries(payload: CompareRequest, db: Session = Depends(get_db)):
    with analysis_errors("Before query: "):
        before = analyze_sql(db, payload.before_query, runs=COMPARE_RUNS)
    with analysis_errors("After query: "):
        after = analyze_sql(db, payload.after_query, runs=COMPARE_RUNS)

    before = save_analysis_safely(db, before)
    after = save_analysis_safely(db, after)

    return compare_analyses(before, after, runs=COMPARE_RUNS)
