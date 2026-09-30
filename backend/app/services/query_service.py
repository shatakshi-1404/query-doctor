from psycopg2 import errors as pg_errors
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import Session

from app.core.config import settings


class QueryTimeoutError(Exception):
    """The query ran longer than the allowed analysis time."""


class QueryExecutionError(Exception):
    """PostgreSQL rejected the query (syntax error, unknown table, etc.)."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class DatabaseUnavailableError(Exception):
    """We could not talk to the database."""


def _friendly_message(error: DBAPIError) -> str:
    diagnostics = getattr(error.orig, "diag", None)
    message = getattr(diagnostics, "message_primary", None)
    return message or "The database could not run this query."


def run_explain_analyze(db: Session, sql: str) -> list[dict]:
    """
    Run EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) for an already-validated query
    and return PostgreSQL's raw plan JSON.
    """
    explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}"

    try:
        # Must be the first statement of the transaction.
        db.execute(text("SET TRANSACTION READ ONLY"))
        db.execute(
            text("SELECT set_config('statement_timeout', :ms, true)"),
            {"ms": str(settings.query_timeout_ms)},
        )
        # Escape ':' so SQLAlchemy's text() doesn't mistake ':word' for a bind parameter.
        result = db.execute(text(explain_sql.replace(":", "\\:")))
        return result.scalar()

    except OperationalError as error:
        if isinstance(error.orig, pg_errors.QueryCanceled):
            raise QueryTimeoutError() from error
        raise DatabaseUnavailableError() from error

    except DBAPIError as error:
        raise QueryExecutionError(_friendly_message(error)) from error

    finally:
        db.rollback()
