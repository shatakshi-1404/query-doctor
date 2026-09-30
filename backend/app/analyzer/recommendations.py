import re
from dataclasses import dataclass, field

from app.analyzer.issues import Issue

# Only names matching this pattern are ever placed into suggested SQL.
_SAFE_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")

# Finds "column <operator>" inside PostgreSQL's Filter text, e.g.
#   ((city)::text = 'Mumbai'::text)   ->  ("city", "=")
#   (quantity > 3)                    ->  ("quantity", ">")
_COMPARISON = re.compile(
    r"\(*(?:[a-z_][a-z0-9_]*\.)?([a-z_][a-z0-9_]*)\)*"
    r"(?:::[a-z_ ]+(?:\[\])?)?\)*\s*(=|<>|!=|<=|>=|<|>)"
)

# Filters wrapped in a function need an expression index, so we don't guess.
_FUNCTION_CALL = re.compile(
    r"\b(lower|upper|date|date_trunc|substr|substring|coalesce|extract|to_char)\s*\("
)

_MAX_INDEX_COLUMNS = 3


@dataclass
class Recommendation:
    title: str
    description: str
    sql_suggestion: str | None = None
    relation_name: str | None = None
    related_rule_ids: list[str] = field(default_factory=list)


def _index_candidate(relation_name: str | None, filter_text: str | None) -> tuple[list[str], str] | None:
    """
    Try to build a CREATE INDEX statement from a scan filter.
    Returns (columns, statement) or None when we can't do it safely.
    """
    if not relation_name or not _SAFE_IDENTIFIER.match(relation_name):
        return None
    if not filter_text:
        return None
    if " OR " in filter_text or "~~" in filter_text or _FUNCTION_CALL.search(filter_text):
        return None

    equality_columns: list[str] = []
    range_columns: list[str] = []

    for column, operator in _COMPARISON.findall(filter_text):
        if operator in ("<>", "!="):
            continue  # "not equal" filters are rarely helped by an index
        if column in equality_columns or column in range_columns:
            continue
        if operator == "=":
            equality_columns.append(column)
        else:
            range_columns.append(column)

    columns = (equality_columns + range_columns)[:_MAX_INDEX_COLUMNS]
    if not columns or not all(_SAFE_IDENTIFIER.match(c) for c in columns):
        return None

    index_name = f"idx_{relation_name}_{'_'.join(columns)}"[:63]  # PostgreSQL name limit
    statement = f"CREATE INDEX {index_name}\nON {relation_name}({', '.join(columns)});"
    return columns, statement


def _index_recommendation(issue: Issue, related_rule_ids: list[str]) -> Recommendation:
    table = issue.relation_name or "the table"
    filter_text = issue.metrics.get("filter")
    discarded = f"{issue.metrics.get('discard_ratio', 0):.0%}"
    candidate = _index_candidate(issue.relation_name, filter_text)

    if candidate is None:
        return Recommendation(
            title=f"Review indexes for the filter on {table}",
            description=(
                f"The filter {filter_text} discarded {discarded} of the rows read from "
                f"{table}. Check whether the filtered columns are indexed. We could not "
                "safely suggest an exact index for this kind of filter (for example "
                "OR conditions, LIKE patterns, or functions applied to a column)."
            ),
            relation_name=issue.relation_name,
            related_rule_ids=related_rule_ids,
        )

    columns, statement = candidate
    column_list = ", ".join(columns)
    order_note = (
        " In a multi-column index, column order matters: equality columns come "
        "first, then range columns."
        if len(columns) > 1
        else ""
    )

    return Recommendation(
        title=f"Consider an index on {table}({column_list})",
        description=(
            f"The filter {filter_text} discarded {discarded} of the rows read from "
            f"{table}. Potential index candidate: an index on ({column_list}) may let "
            f"PostgreSQL find matching rows without reading the whole table.{order_note} "
            "Indexes add disk usage and slow down writes, and PostgreSQL may still "
            "choose not to use one, so re-analyze the query after creating it."
        ),
        sql_suggestion=statement,
        relation_name=issue.relation_name,
        related_rule_ids=related_rule_ids,
    )


def build_recommendations(issues: list[Issue]) -> list[Recommendation]:
    recommendations: list[Recommendation] = []

    # 1) Index suggestions first. A LARGE_SEQ_SCAN on the same scan is merged in.
    covered_scans: set[tuple[str | None, int | None]] = set()

    for issue in issues:
        if issue.rule_id != "SEQ_SCAN_WITH_FILTER":
            continue
        scan_key = (issue.relation_name, issue.metrics.get("rows_scanned"))
        rule_ids = ["SEQ_SCAN_WITH_FILTER"]
        if any(
            other.rule_id == "LARGE_SEQ_SCAN"
            and (other.relation_name, other.metrics.get("rows_scanned")) == scan_key
            for other in issues
        ):
            rule_ids.append("LARGE_SEQ_SCAN")
            covered_scans.add(scan_key)
        recommendations.append(_index_recommendation(issue, rule_ids))

    # 2) Everything else, in the order the issues were found.
    seen_statistics: set[str | None] = set()

    for issue in issues:
        table = issue.relation_name or "this step"

        if issue.rule_id == "LARGE_SEQ_SCAN":
            if (issue.relation_name, issue.metrics.get("rows_scanned")) in covered_scans:
                continue
            recommendations.append(
                Recommendation(
                    title=f"Reduce the rows read from {table}",
                    description=(
                        f"PostgreSQL read about {issue.metrics['rows_scanned']:,} rows "
                        f"and returned {issue.metrics['rows_returned']:,}. If you do not "
                        "need every row, add a selective WHERE condition or a LIMIT, "
                        "and select only the columns you need."
                    ),
                    relation_name=issue.relation_name,
                    related_rule_ids=[issue.rule_id],
                )
            )

        elif issue.rule_id == "HIGH_ACTUAL_TIME":
            # Skip if a more specific issue already covers the same plan node.
            if any(
                other is not issue
                and other.node_type == issue.node_type
                and other.relation_name == issue.relation_name
                for other in issues
            ):
                continue
            recommendations.append(
                Recommendation(
                    title=f"Start with the {issue.node_type} step",
                    description=(
                        f"{issue.what_happened} Focus optimization effort here first: "
                        "look for ways to make this step read fewer rows or run "
                        "fewer times."
                    ),
                    relation_name=issue.relation_name,
                    related_rule_ids=[issue.rule_id],
                )
            )

        elif issue.rule_id == "ESTIMATE_MISMATCH":
            if issue.relation_name in seen_statistics:
                continue
            seen_statistics.add(issue.relation_name)
            can_suggest = issue.relation_name and _SAFE_IDENTIFIER.match(issue.relation_name)
            recommendations.append(
                Recommendation(
                    title="Check table statistics",
                    description=(
                        f"The planner's row estimate was about {issue.metrics['ratio']:.0f}x "
                        "away from the actual count. Refreshing statistics with ANALYZE is "
                        "a reasonable first step. If the estimate stays far off, the cause "
                        "may be an unusual data distribution, correlated columns, or a "
                        "query that stops early (for example with LIMIT)."
                    ),
                    sql_suggestion=f"ANALYZE {issue.relation_name};" if can_suggest else None,
                    relation_name=issue.relation_name,
                    related_rule_ids=[issue.rule_id],
                )
            )

        elif issue.rule_id == "EXPENSIVE_SORT":
            recommendations.append(
                Recommendation(
                    title="Reduce the cost of sorting",
                    description=(
                        f"Sorting {issue.metrics['rows_sorted']:,} rows took about "
                        f"{issue.metrics['sort_time_ms']} ms. Things to investigate: return "
                        "fewer rows (WHERE or LIMIT), select fewer columns, or add an index "
                        "matching the ORDER BY columns so rows can come out already sorted."
                    ),
                    related_rule_ids=[issue.rule_id],
                )
            )

        elif issue.rule_id == "NESTED_LOOP_COST":
            recommendations.append(
                Recommendation(
                    title="Check indexes on the join columns",
                    description=(
                        f"A nested loop produced {issue.metrics['rows_produced']:,} rows and "
                        f"repeated its inner side up to {issue.metrics['inner_loops']:,} "
                        "times. Confirm the columns in the JOIN condition are indexed on the "
                        "inner table, and review whether the join needs this many rows."
                    ),
                    related_rule_ids=[issue.rule_id],
                )
            )

    return recommendations
