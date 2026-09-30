from app.analyzer.issues import Issue, Severity
from app.analyzer.parser import ParsedPlan, walk
from app.analyzer.thresholds import AnalyzerThresholds


def check_nested_loop_cost(plan: ParsedPlan, thresholds: AnalyzerThresholds) -> list[Issue]:
    """
    Rule 6: a Nested Loop is only reported when it produces many rows
    AND takes significant time. Nested loops themselves are not a problem.
    """
    issues: list[Issue] = []

    for node in walk(plan.root):
        if node.node_type != "Nested Loop":
            continue

        rows = node.actual_rows * max(node.actual_loops, 1)

        # Inclusive time on purpose: a nested loop's cost is mostly the
        # repeated inner work done by its children.
        if (
            rows < thresholds.nested_loop_min_rows
            or node.total_time_ms < thresholds.nested_loop_min_ms
        ):
            continue

        inner_loops = max((child.actual_loops for child in node.children), default=1)

        issues.append(
            Issue(
                rule_id="NESTED_LOOP_COST",
                title="Nested Loop May Be Costly",
                severity=Severity.WARNING,
                node_type=node.node_type,
                relation_name=None,
                what_happened=(
                    f"A Nested Loop produced {rows:,} rows and took about "
                    f"{node.total_time_ms:.1f} ms; its inner side ran up to "
                    f"{inner_loops:,} times."
                ),
                why_it_matters=(
                    "A nested loop repeats its inner lookup for every outer row. "
                    "That is efficient for small inputs but adds up with many rows."
                ),
                what_to_investigate=(
                    "Nested loop may be contributing to query cost. Review the join "
                    "conditions and check that the joined columns are indexed."
                ),
                metrics={
                    "rows_produced": rows,
                    "node_time_ms": round(node.total_time_ms, 3),
                    "inner_loops": inner_loops,
                },
            )
        )

    return issues
