from app.analyzer.issues import Issue, Severity
from app.analyzer.parser import ParsedPlan, own_time_ms, walk
from app.analyzer.thresholds import AnalyzerThresholds


def check_expensive_sort(plan: ParsedPlan, thresholds: AnalyzerThresholds) -> list[Issue]:
    """Rule 5: a Sort step that takes a significant amount of time."""
    issues: list[Issue] = []

    for node in walk(plan.root):
        if node.node_type != "Sort":
            continue

        own = own_time_ms(node)
        if own < thresholds.sort_min_ms:
            continue

        rows_sorted = node.actual_rows * max(node.actual_loops, 1)

        issues.append(
            Issue(
                rule_id="EXPENSIVE_SORT",
                title="Expensive Sort",
                severity=Severity.WARNING,
                node_type=node.node_type,
                relation_name=node.relation_name,
                what_happened=(
                    f"Sorting about {rows_sorted:,} rows took roughly {own:.1f} ms "
                    "(not counting the time to read them)."
                ),
                why_it_matters=(
                    "Sorting large result sets takes time and memory, and it must "
                    "finish before the first row can be returned."
                ),
                what_to_investigate=(
                    "Potential expensive sort detected. Review the ORDER BY clause, "
                    "whether an index could provide rows already in order, and "
                    "the amount of data being sorted (columns selected and rows returned)."
                ),
                metrics={
                    "rows_sorted": rows_sorted,
                    "sort_time_ms": round(own, 3),
                },
            )
        )

    return issues
