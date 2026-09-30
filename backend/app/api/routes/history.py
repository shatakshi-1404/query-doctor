from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.analysis import AnalyzeResponse
from app.schemas.comparison import CompareResponse
from app.schemas.history import HistoryItem
from app.services.comparison_service import compare_analyses
from app.services.history_service import get_analysis, list_history

router = APIRouter()


@router.get("/compare", response_model=CompareResponse)
def compare_saved(before_id: int, after_id: int, db: Session = Depends(get_db)):
    # Must be declared before "/{analysis_id}" or FastAPI would try to match
    # "compare" as an analysis_id and return a 422 instead of reaching this route.
    before = get_analysis(db, before_id)
    after = get_analysis(db, after_id)
    if before is None or after is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return compare_analyses(before, after, runs=1)


@router.get("", response_model=list[HistoryItem])
def recent_history(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    return list_history(db, limit)


@router.get("/{analysis_id}", response_model=AnalyzeResponse)
def analysis_detail(analysis_id: int, db: Session = Depends(get_db)):
    result = get_analysis(db, analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return result
