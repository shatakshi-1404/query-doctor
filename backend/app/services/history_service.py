import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AnalysisRecord, QueryRecord
from app.schemas.analysis import AnalyzeResponse
from app.schemas.history import HistoryItem

logger = logging.getLogger("querydoctor")


def save_analysis(db: Session, result: AnalyzeResponse) -> int:
    """Store an analysis and return its id. Re-uses the query row if the same text was analyzed before."""
    query_record = db.scalar(
        select(QueryRecord).where(QueryRecord.query_text == result.query)
    )
    if query_record is None:
        query_record = QueryRecord(query_text=result.query)
        db.add(query_record)
        db.flush()  # sends the INSERT so query_record.id is available

    analysis = AnalysisRecord(
        query_id=query_record.id,
        planning_time=result.planning_time_ms,
        execution_time=result.execution_time_ms,
        rows_returned=result.rows_returned,
        issues_count=len(result.issues),
        result=result.model_dump(mode="json"),
    )
    db.add(analysis)
    db.flush()
    analysis_id = analysis.id
    db.commit()
    return analysis_id


def save_analysis_safely(db: Session, result: AnalyzeResponse) -> AnalyzeResponse:
    """Save to history; if saving fails, still return the analysis (without an id)."""
    try:
        analysis_id = save_analysis(db, result)
        return result.model_copy(update={"analysis_id": analysis_id})
    except Exception:
        db.rollback()
        logger.exception("Could not save analysis to history.")
        return result


def list_history(db: Session, limit: int = 50) -> list[HistoryItem]:
    # Select only the summary columns so the big JSON column is not loaded for every row.
    statement = (
        select(
            AnalysisRecord.id,
            QueryRecord.query_text,
            AnalysisRecord.planning_time,
            AnalysisRecord.execution_time,
            AnalysisRecord.rows_returned,
            AnalysisRecord.issues_count,
            AnalysisRecord.created_at,
        )
        .join(QueryRecord, QueryRecord.id == AnalysisRecord.query_id)
        .order_by(AnalysisRecord.created_at.desc(), AnalysisRecord.id.desc())
        .limit(limit)
    )
    return [
        HistoryItem(
            analysis_id=row.id,
            query_text=row.query_text,
            planning_time_ms=row.planning_time,
            execution_time_ms=row.execution_time,
            rows_returned=row.rows_returned,
            issues_count=row.issues_count,
            created_at=row.created_at,
        )
        for row in db.execute(statement)
    ]


def get_analysis(db: Session, analysis_id: int) -> AnalyzeResponse | None:
    record = db.get(AnalysisRecord, analysis_id)
    if record is None:
        return None
    data = dict(record.result)
    data["analysis_id"] = record.id
    data["created_at"] = record.created_at
    return AnalyzeResponse(**data)
