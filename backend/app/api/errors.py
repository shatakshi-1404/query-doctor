from contextlib import contextmanager

from fastapi import HTTPException

from app.analyzer.parser import InvalidPlanError
from app.services.query_service import (
    DatabaseUnavailableError,
    QueryExecutionError,
    QueryTimeoutError,
)
from app.services.query_validator import InvalidQueryError


@contextmanager
def analysis_errors(prefix: str = ""):
    """Turn analysis exceptions into friendly HTTP errors. `prefix` says which query failed."""
    try:
        yield
    except InvalidQueryError as error:
        raise HTTPException(status_code=400, detail=f"{prefix}{error.message}")
    except QueryExecutionError as error:
        raise HTTPException(
            status_code=400,
            detail=f"{prefix}Unable to analyze query. Reason: {error.message}",
        )
    except QueryTimeoutError:
        raise HTTPException(
            status_code=408, detail=f"{prefix}Query exceeded the allowed analysis time."
        )
    except DatabaseUnavailableError:
        raise HTTPException(status_code=503, detail="Database is unavailable.")
    except InvalidPlanError:
        raise HTTPException(
            status_code=500, detail="Unable to read the PostgreSQL execution plan."
        )
