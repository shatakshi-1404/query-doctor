from app.schemas.analysis import AnalyzeResponse, PlanNodeOut
from app.schemas.comparison import CompareResponse, MetricComparison

# Changes smaller than BOTH of these are treated as normal run-to-run variation.
MIN_CHANGE_PCT = 10.0
MIN_CHANGE_MS = 0.5


def _fmt_ms(ms: float) -> str:
    return f"{ms:.2f}" if ms < 1 else f"{ms:.1f}"


def _pct_change(before: float, after: float) -> float | None:
    if before == 0:
        return None
    return (after - before) / before * 100


def _verdict(before_ms: float, after_ms: float) -> str:
    diff = before_ms - after_ms
    if abs(diff) < MIN_CHANGE_MS:
        return "no_significant_change"
    if before_ms > 0 and abs(diff) / before_ms * 100 < MIN_CHANGE_PCT:
        return "no_significant_change"
    return "improved" if diff > 0 else "regressed"


def _summary(verdict: str, before_ms: float, after_ms: float) -> str:
    change = abs(before_ms - after_ms) / before_ms * 100 if before_ms > 0 else 0.0
    before_text, after_text = _fmt_ms(before_ms), _fmt_ms(after_ms)

    if verdict == "improved":
        return f"Execution time improved by {change:.0f}% (from {before_text} ms to {after_text} ms)."
    if verdict == "regressed":
        return f"Execution time got worse by {change:.0f}% (from {before_text} ms to {after_text} ms)."
    return (
        f"No significant difference in execution time ({before_text} ms vs {after_text} ms). "
        "Changes this small are within normal run-to-run variation."
    )


def _outline(node: PlanNodeOut) -> str:
    """A compact one-line description of a plan tree, e.g. 'Hash Join [Seq Scan(orders), Hash [...]]'."""
    label = node.node_type + (f"({node.relation_name})" if node.relation_name else "")
    if not node.children:
        return label
    return f"{label} [{', '.join(_outline(child) for child in node.children)}]"


def _issue_labels(result: AnalyzeResponse) -> dict[tuple[str, str | None], str]:
    return {
        (issue.rule_id, issue.relation_name): (
            f"{issue.title} on {issue.relation_name}" if issue.relation_name else issue.title
        )
        for issue in result.issues
    }


def _buffers_touched(result: AnalyzeResponse) -> int:
    # Buffer counts are cumulative, so the root node already includes its children.
    return result.plan.shared_hit_blocks + result.plan.shared_read_blocks


def _lower_is_better(before: float, after: float) -> bool | None:
    if before == after:
        return None
    return after < before


def _metric(
    key: str, label: str, unit: str | None, before: float, after: float, better: bool | None
) -> MetricComparison:
    return MetricComparison(
        key=key,
        label=label,
        unit=unit,
        before=before,
        after=after,
        change_pct=_pct_change(before, after),
        better=better,
    )


def compare_analyses(before: AnalyzeResponse, after: AnalyzeResponse, runs: int = 1) -> CompareResponse:
    """Compare two analyses using only the numbers PostgreSQL measured."""
    verdict = _verdict(before.execution_time_ms, after.execution_time_ms)

    execution_better = {"improved": True, "regressed": False}.get(verdict)

    metrics = [
        _metric("execution_time", "Execution Time", "ms",
                before.execution_time_ms, after.execution_time_ms, execution_better),
        _metric("planning_time", "Planning Time", "ms",
                before.planning_time_ms, after.planning_time_ms, None),
        _metric("rows_returned", "Rows Returned", None,
                before.rows_returned, after.rows_returned, None),
        _metric("issues_count", "Issues Detected", None,
                len(before.issues), len(after.issues),
                _lower_is_better(len(before.issues), len(after.issues))),
        _metric("buffers", "Buffers Touched", None,
                _buffers_touched(before), _buffers_touched(after),
                _lower_is_better(_buffers_touched(before), _buffers_touched(after))),
    ]

    before_issues, after_issues = _issue_labels(before), _issue_labels(after)
    resolved = [label for key, label in before_issues.items() if key not in after_issues]
    new = [label for key, label in after_issues.items() if key not in before_issues]

    notes: list[str] = []
    if before.rows_returned != after.rows_returned:
        notes.append(
            f"The queries returned different numbers of rows "
            f"({before.rows_returned:,} vs {after.rows_returned:,}), so they may not be "
            "equivalent. Compare the timings with care."
        )
    outline_before, outline_after = _outline(before.plan), _outline(after.plan)
    if outline_before != outline_after:
        notes.append(
            f"The execution plan changed. Before: {outline_before}. After: {outline_after}."
        )
    if runs > 1:
        notes.append(
            f"Each query was run {runs} times; the run with the median execution time is shown."
        )

    return CompareResponse(
        before=before,
        after=after,
        metrics=metrics,
        verdict=verdict,
        summary=_summary(verdict, before.execution_time_ms, after.execution_time_ms),
        resolved_issues=resolved,
        new_issues=new,
        notes=notes,
        runs=runs,
    )
