from app.analyzer.general_rules import check_estimate_mismatch, check_high_actual_time
from app.analyzer.issues import Issue
from app.analyzer.join_rules import check_nested_loop_cost
from app.analyzer.parser import ParsedPlan
from app.analyzer.scan_rules import check_large_seq_scan, check_seq_scan_with_filter
from app.analyzer.sort_rules import check_expensive_sort
from app.analyzer.thresholds import AnalyzerThresholds

RULES = [
    check_large_seq_scan,
    check_seq_scan_with_filter,
    check_high_actual_time,
    check_estimate_mismatch,
    check_expensive_sort,
    check_nested_loop_cost,
]


def run_rules(plan: ParsedPlan, thresholds: AnalyzerThresholds | None = None) -> list[Issue]:
    thresholds = thresholds or AnalyzerThresholds()
    issues: list[Issue] = []
    for rule in RULES:
        issues.extend(rule(plan, thresholds))
    return issues
