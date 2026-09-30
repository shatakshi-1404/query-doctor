from app.analyzer.issues import Issue, Severity
from app.analyzer.parser import ParsedPlan, own_time_ms, walk
from app.analyzer.thresholds import AnalyzerThresholds


def check_high_actual_time(plan: ParsedPlan, thresholds: AnalyzerThresholds) -> list[Issue]:
    """Rule 3: one plan node accounts for a large share of the total execution time."""
    total = plan.execution_time_ms
    if total <= 0:
        return []

    issues: list[Issue] = []

    for node in walk(plan.root):
        own = own_time_ms(node)
        share = own / total

        if own < thresholds.high_time_min_ms or share < thresholds.high_time_share:
            continue

        target = f" on {node.relation_name}" if node.relation_name else ""

        issues.append(
            Issue(
                rule_id="HIGH_ACTUAL_TIME",
                title="Potential Bottleneck",
                severity=Severity.WARNING,
                node_type=node.node_type,
                relation_name=node.relation_name,
                what_happened=(
                    f"{node.node_type}{target} spent about {own:.1f} ms of its own "
                    f"time, roughly {share:.0%} of the {total:.1f} ms execution time."
                ),
                why_it_matters=(
                    "The step that takes the largest share of time is usually the "
                    "best place to start, since improving it can change the total the most."
                ),
                what_to_investigate=(
                    "Potential bottleneck detected. Review what this step does and "
                    "whether it could read fewer rows, use an index, or run fewer times."
                ),
                metrics={
                    "own_time_ms": round(own, 3),
                    "share_of_total": round(share, 3),
                    "execution_time_ms": round(total, 3),
                    "loops": node.actual_loops,
                },
            )
        )

    return issues


def check_estimate_mismatch(plan: ParsedPlan, thresholds: AnalyzerThresholds) -> list[Issue]:
    """Rule 4: the planner's row estimate is far from the actual row count."""
    issues: list[Issue] = []

    for node in walk(plan.root):
        if node.actual_loops == 0:
            continue  # this node never ran

        estimated = node.plan_rows
        actual = node.actual_rows
        bigger = max(estimated, actual)
        smaller = max(min(estimated, actual), 1)  # avoid dividing by zero

        if bigger < thresholds.estimate_min_rows:
            continue

        ratio = bigger / smaller
        if ratio < thresholds.estimate_ratio:
            continue

        direction = "underestimated" if actual > estimated else "overestimated"
        target = f" on {node.relation_name}" if node.relation_name else ""

        issues.append(
            Issue(
                rule_id="ESTIMATE_MISMATCH",
                title="Row Estimate Differs From Actual",
                severity=Severity.WARNING,
                node_type=node.node_type,
                relation_name=node.relation_name,
                what_happened=(
                    f"For {node.node_type}{target}, PostgreSQL {direction} the row "
                    f"count: estimated {estimated:,}, actual {actual:,} "
                    f"(about {ratio:.0f}x off)."
                ),
                why_it_matters=(
                    "The planner chooses scans and join methods based on these "
                    "estimates, so large errors can lead to a less suitable plan."
                ),
                what_to_investigate=(
                    "Cardinality estimate differs significantly from actual rows. "
                    "Possible causes include stale statistics, unusual data "
                    "distribution, or a query that stops early (for example with LIMIT)."
                ),
                metrics={
                    "estimated_rows": estimated,
                    "actual_rows": actual,
                    "ratio": round(ratio, 1),
                },
            )
        )

    return issues
