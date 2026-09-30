from typing import Iterator

from app.analyzer.issues import Issue, Severity
from app.analyzer.parser import ParsedPlan, PlanNode, walk
from app.analyzer.thresholds import AnalyzerThresholds

SEQ_SCAN_TYPES = {"Seq Scan", "Parallel Seq Scan"}


def _seq_scans(plan: ParsedPlan) -> Iterator[PlanNode]:
    for node in walk(plan.root):
        if node.node_type in SEQ_SCAN_TYPES:
            yield node


def _rows_kept_and_removed(node: PlanNode) -> tuple[int, int]:
    """Row counts in a plan are per loop, so multiply by loops for the real total."""
    loops = max(node.actual_loops, 1)
    return node.actual_rows * loops, node.rows_removed_by_filter * loops


def check_large_seq_scan(plan: ParsedPlan, thresholds: AnalyzerThresholds) -> list[Issue]:
    """Rule 1: flag sequential scans that read a large number of rows."""
    issues: list[Issue] = []

    for node in _seq_scans(plan):
        kept, removed = _rows_kept_and_removed(node)
        rows_scanned = kept + removed

        if rows_scanned < thresholds.seq_scan_min_rows:
            continue

        severity = (
            Severity.CRITICAL
            if rows_scanned >= thresholds.seq_scan_critical_rows
            else Severity.WARNING
        )
        table = node.relation_name or "a table"

        issues.append(
            Issue(
                rule_id="LARGE_SEQ_SCAN",
                title="Large Sequential Scan",
                severity=severity,
                node_type=node.node_type,
                relation_name=node.relation_name,
                what_happened=(
                    f"PostgreSQL read about {rows_scanned:,} rows from {table} "
                    f"one by one and returned {kept:,}."
                ),
                why_it_matters=(
                    "Reading every row is fine for small tables or when most rows "
                    "are needed, but on a large table it can account for much of "
                    "the query's execution time."
                ),
                what_to_investigate=(
                    "Large sequential scan detected. Consider whether a suitable "
                    "index exists for the columns used in your WHERE or JOIN "
                    "conditions, and whether you really need this many rows."
                ),
                metrics={
                    "rows_scanned": rows_scanned,
                    "rows_returned": kept,
                    "node_time_ms": round(node.total_time_ms, 3),
                },
            )
        )

    return issues


def check_seq_scan_with_filter(plan: ParsedPlan, thresholds: AnalyzerThresholds) -> list[Issue]:
    """Rule 2: a sequential scan whose WHERE filter throws away most of the rows it reads."""
    issues: list[Issue] = []

    for node in _seq_scans(plan):
        if not node.filter_condition:
            continue

        kept, removed = _rows_kept_and_removed(node)
        rows_scanned = kept + removed
        if rows_scanned == 0:
            continue

        discard_ratio = removed / rows_scanned
        if (
            removed < thresholds.filter_min_rows_removed
            or discard_ratio < thresholds.filter_min_discard_ratio
        ):
            continue

        table = node.relation_name or "a table"

        issues.append(
            Issue(
                rule_id="SEQ_SCAN_WITH_FILTER",
                title="Filter Applied After Full Scan",
                severity=Severity.WARNING,
                node_type=node.node_type,
                relation_name=node.relation_name,
                what_happened=(
                    f"PostgreSQL read {rows_scanned:,} rows from {table} and "
                    f"discarded {removed:,} of them ({discard_ratio:.0%}) using the filter."
                ),
                why_it_matters=(
                    "When a filter keeps only a small fraction of a table, "
                    "PostgreSQL may be doing far more reading than necessary."
                ),
                what_to_investigate=(
                    "Potential index candidate: check whether the column(s) in this "
                    f"filter are indexed: {node.filter_condition}. An index helps "
                    "most when the filter matches a small share of the table."
                ),
                metrics={
                    "rows_scanned": rows_scanned,
                    "rows_kept": kept,
                    "rows_removed": removed,
                    "discard_ratio": round(discard_ratio, 3),
                    "filter": node.filter_condition,
                },
            )
        )

    return issues
