import pytest

from app.services.query_validator import InvalidQueryError, validate_read_only_query

ACCEPTED = [
    "SELECT * FROM users WHERE city = 'Mumbai';",
    "  select id from users",
    "sElEcT 1",
    "WITH t AS (SELECT 1) SELECT * FROM t",
    "-- find users\nSELECT * FROM users",
    "/* note */ SELECT * FROM users",
    "SELECT created_at, deleted FROM orders",  # 'deleted' is not the word DELETE
    "SELECT u.name FROM users u JOIN orders o ON o.user_id = u.id",
]

REJECTED = [
    ("DELETE FROM users", "read-only"),
    ("insert into users values (1)", "read-only"),
    ("UPDATE users SET city = 'x'", "read-only"),
    ("DROP TABLE users", "read-only"),
    ("ALTER TABLE users ADD COLUMN x int", "read-only"),
    ("TRUNCATE users", "read-only"),
    ("CREATE INDEX i ON users(city)", "read-only"),
    ("GRANT ALL ON users TO bob", "read-only"),
    ("REVOKE ALL ON users FROM bob", "read-only"),
    ("EXPLAIN SELECT * FROM users", "read-only"),
    ("SELECT * INTO backup FROM users", "INTO"),
    ("WITH d AS (DELETE FROM users RETURNING *) SELECT * FROM d", "DELETE"),
    ("SELECT 1; DROP TABLE users", "single"),
    ("SELECT 1; SELECT 2", "single"),
    ("", "empty"),
    ("   \n  ", "empty"),
]


@pytest.mark.parametrize("sql", ACCEPTED)
def test_read_only_queries_are_accepted(sql):
    assert validate_read_only_query(sql)  # returns the cleaned, non-empty query


@pytest.mark.parametrize("sql, expected_fragment", REJECTED)
def test_unsafe_or_invalid_queries_are_rejected(sql, expected_fragment):
    with pytest.raises(InvalidQueryError) as error:
        validate_read_only_query(sql)
    assert expected_fragment in error.value.message


def test_none_is_treated_as_empty():
    with pytest.raises(InvalidQueryError) as error:
        validate_read_only_query(None)
    assert "empty" in error.value.message


def test_trailing_semicolon_and_spaces_are_removed():
    assert validate_read_only_query("  SELECT 1 ;  ") == "SELECT 1"


def test_query_at_the_length_limit_is_accepted():
    sql = "SELECT " + "a" * (10_000 - len("SELECT "))
    assert len(sql) == 10_000
    assert validate_read_only_query(sql) == sql


def test_query_over_the_length_limit_is_rejected():
    with pytest.raises(InvalidQueryError) as error:
        validate_read_only_query("SELECT " + "a" * 10_001)
    assert "too long" in error.value.message


def test_known_limitation_keyword_inside_a_string_is_rejected():
    # Documented in the validator: the check is a keyword scan, not a SQL parser,
    # so it over-rejects in order to stay safe. This test records that decision.
    with pytest.raises(InvalidQueryError):
        validate_read_only_query("SELECT * FROM logs WHERE action = 'delete'")
