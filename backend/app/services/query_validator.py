import re

MAX_QUERY_LENGTH = 10_000

FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "CREATE", "GRANT", "REVOKE",
    "COPY", "INTO", "MERGE", "CALL", "DO", "EXECUTE", "VACUUM",
]

FORBIDDEN_PATTERN = re.compile(
    r"\b(" + "|".join(FORBIDDEN_KEYWORDS) + r")\b", re.IGNORECASE
)

ALLOWED_START_PATTERN = re.compile(r"(select|with)\b", re.IGNORECASE)


class InvalidQueryError(Exception):
    """Raised when a query is not allowed to be analyzed."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _skip_leading_noise(sql: str) -> str:
    """Remove leading whitespace and comments so we can see the first real keyword."""
    while True:
        stripped = sql.lstrip()
        if stripped.startswith("--"):
            newline = stripped.find("\n")
            sql = "" if newline == -1 else stripped[newline + 1:]
        elif stripped.startswith("/*"):
            end = stripped.find("*/")
            sql = "" if end == -1 else stripped[end + 2:]
        else:
            return stripped


def validate_read_only_query(sql: str) -> str:
    """
    Check that `sql` is a single read-only SELECT/WITH query.
    Returns the cleaned query (trailing semicolon removed) or raises InvalidQueryError.

    LIMITATIONS (beginner-level validation, not a full SQL parser):
    - Keywords are matched anywhere in the text, even inside string literals or
      comments, so `WHERE action = 'delete'` is rejected. Safe, but over-strict.
    - Any ';' other than a final one is rejected, even inside a string.
    - Read-only functions with side effects are not individually checked.
    - The real safety net is the read-only transaction added in query_service.py.
    """
    if sql is None or not sql.strip():
        raise InvalidQueryError("Query cannot be empty.")

    if len(sql) > MAX_QUERY_LENGTH:
        raise InvalidQueryError(
            f"Query is too long (maximum {MAX_QUERY_LENGTH} characters)."
        )

    body = sql.strip()
    if body.endswith(";"):
        body = body[:-1].rstrip()

    if ";" in body:
        raise InvalidQueryError("Only a single SQL statement is allowed.")

    first_part = _skip_leading_noise(body)
    if not ALLOWED_START_PATTERN.match(first_part):
        raise InvalidQueryError("Only read-only queries are supported.")

    match = FORBIDDEN_PATTERN.search(body)
    if match:
        raise InvalidQueryError(
            f"Only read-only queries are supported. "
            f"Found disallowed keyword: {match.group(1).upper()}."
        )

    return body
