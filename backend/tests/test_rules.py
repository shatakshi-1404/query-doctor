from dataclasses import FrozenInstanceError

import pytest

from app.analyzer.engine import run_rules
from app.analyzer.general_rules import check_estimate_mismatch, check_high_actual_time
from app.analyzer.issues import Severity
from app.analyzer.join_rules import check_nested_loop_cost
from app.analyzer.scan_rules import check_large_seq_scan, check_seq_scan_with_filter
from app.analyzer.sort_rules import check_expensive_sort
from app.analyzer.thresholds import AnalyzerThresholds
from tests.factories import node, plan_of

T = AnalyzerThresholds()  # the default thresholds


class TestLargeSeqScan:
    def test_flags_a_scan_that_reads_ten_thousand_rows(self):
        scan = node("Seq Scan", relation_name="users", actual_rows=1012,
                    rows_removed_by_filter=8988, total_time_ms=1.85)

        issues = check_large_seq_scan(plan_of(scan), T)

        assert len(issues) == 1
        issue = issues[0]
        assert issue.rule_id == "LARGE_SEQ_SCAN"
        assert issue.severity == Severity.WARNING
        assert issue.relation_name == "users"
        assert issue.metrics["rows_scanned"] == 10_000
        assert issue.metrics["rows_returned"] == 1012

    def test_ignores_a_small_table(self):
        scan = node("Seq Scan", relation_name="products", actual_rows=1000)
        assert check_large_seq_scan(plan_of(scan), T) == []

    def test_a_very_large_scan_is_critical(self):
        scan = node("Seq Scan", relation_name="order_items", actual_rows=150_000)
        assert check_large_seq_scan(plan_of(scan), T)[0].severity == Severity.CRITICAL

    def test_index_scans_are_not_flagged(self):
        scan = node("Index Scan", relation_name="users", actual_rows=100_000)
        assert check_large_seq_scan(plan_of(scan), T) == []

    def test_finds_a_scan_nested_inside_a_join(self):
        scan = node("Seq Scan", relation_name="orders", actual_rows=50_000)
        join = node("Hash Join", children=[scan, node("Hash")])
        issues = check_large_seq_scan(plan_of(join), T)
        assert [i.relation_name for i in issues] == ["orders"]

    def test_repeated_scans_are_multiplied_by_loops(self):
        scan = node("Seq Scan", relation_name="t", actual_rows=1000, actual_loops=10)
        assert check_large_seq_scan(plan_of(scan), T)[0].metrics["rows_scanned"] == 10_000

    def test_wording_is_careful_not_absolute(self):
        scan = node("Seq Scan", relation_name="users", actual_rows=10_000)
        text = check_large_seq_scan(plan_of(scan), T)[0].what_to_investigate
        assert "Consider" in text
        assert "always" not in text.lower()


class TestSeqScanWithFilter:
    def test_flags_a_filter_that_discards_most_rows(self):
        scan = node("Seq Scan", relation_name="users", filter_condition="(city = 'x')",
                    actual_rows=1012, rows_removed_by_filter=8988)

        issues = check_seq_scan_with_filter(plan_of(scan), T)

        assert len(issues) == 1
        assert issues[0].rule_id == "SEQ_SCAN_WITH_FILTER"
        assert issues[0].metrics["rows_removed"] == 8988
        assert issues[0].metrics["filter"] == "(city = 'x')"
        assert "Potential index candidate" in issues[0].what_to_investigate

    def test_a_scan_without_a_filter_is_not_flagged(self):
        scan = node("Seq Scan", relation_name="users", actual_rows=10_000)
        assert check_seq_scan_with_filter(plan_of(scan), T) == []

    def test_a_filter_that_keeps_most_rows_is_not_flagged(self):
        scan = node("Seq Scan", relation_name="users", filter_condition="(x > 1)",
                    actual_rows=9000, rows_removed_by_filter=1000)
        assert check_seq_scan_with_filter(plan_of(scan), T) == []

    def test_too_few_discarded_rows_is_not_flagged(self):
        scan = node("Seq Scan", relation_name="users", filter_condition="(x = 1)",
                    actual_rows=10, rows_removed_by_filter=500)
        assert check_seq_scan_with_filter(plan_of(scan), T) == []


class TestHighActualTime:
    def test_flags_the_node_that_dominates_by_its_own_time(self):
        scan = node("Seq Scan", relation_name="orders", total_time_ms=30)
        sort = node("Sort", total_time_ms=90, children=[scan])

        issues = check_high_actual_time(plan_of(sort, execution_time_ms=100), T)

        assert [i.node_type for i in issues] == ["Sort"]  # 60 ms of its own; the scan has 30 ms
        assert issues[0].metrics["own_time_ms"] == pytest.approx(60)
        assert issues[0].metrics["share_of_total"] == pytest.approx(0.6)

    def test_uses_own_time_so_the_parent_is_not_blamed_for_its_child(self):
        scan = node("Seq Scan", relation_name="orders", total_time_ms=95)
        limit = node("Limit", total_time_ms=100, children=[scan])

        issues = check_high_actual_time(plan_of(limit, execution_time_ms=100), T)

        assert [i.node_type for i in issues] == ["Seq Scan"]

    def test_fast_queries_are_not_flagged(self):
        scan = node("Seq Scan", total_time_ms=1.9)
        assert check_high_actual_time(plan_of(scan, execution_time_ms=2.0), T) == []

    def test_zero_execution_time_does_not_crash(self):
        assert check_high_actual_time(plan_of(node(), execution_time_ms=0), T) == []


class TestEstimateMismatch:
    def test_underestimate_is_reported(self):
        n = node("Seq Scan", relation_name="orders", plan_rows=100, actual_rows=50_000)

        issues = check_estimate_mismatch(plan_of(n), T)

        assert len(issues) == 1
        assert "underestimated" in issues[0].what_happened
        assert issues[0].metrics["ratio"] == 500.0

    def test_overestimate_is_reported(self):
        n = node("Seq Scan", relation_name="orders", plan_rows=50_000, actual_rows=100)
        issues = check_estimate_mismatch(plan_of(n), T)
        assert "overestimated" in issues[0].what_happened

    def test_close_estimates_are_ignored(self):
        n = node("Seq Scan", plan_rows=1000, actual_rows=1012)
        assert check_estimate_mismatch(plan_of(n), T) == []

    def test_mismatch_on_tiny_row_counts_is_ignored(self):
        n = node("Seq Scan", plan_rows=2, actual_rows=30)
        assert check_estimate_mismatch(plan_of(n), T) == []

    def test_a_node_that_never_ran_is_skipped(self):
        n = node("Seq Scan", plan_rows=50_000, actual_rows=0, actual_loops=0)
        assert check_estimate_mismatch(plan_of(n), T) == []

    def test_zero_actual_rows_does_not_divide_by_zero(self):
        n = node("Seq Scan", plan_rows=50_000, actual_rows=0, actual_loops=1)
        assert check_estimate_mismatch(plan_of(n), T)[0].metrics["ratio"] == 50_000.0

    def test_does_not_claim_a_definite_cause(self):
        n = node("Seq Scan", plan_rows=100, actual_rows=50_000)
        text = check_estimate_mismatch(plan_of(n), T)[0].what_to_investigate
        assert "Possible causes" in text


class TestExpensiveSort:
    def test_flags_a_slow_sort_using_its_own_time(self):
        scan = node("Seq Scan", relation_name="orders", actual_rows=50_000, total_time_ms=30)
        sort = node("Sort", actual_rows=50_000, total_time_ms=90, children=[scan])

        issues = check_expensive_sort(plan_of(sort), T)

        assert len(issues) == 1
        assert issues[0].metrics["rows_sorted"] == 50_000
        assert issues[0].metrics["sort_time_ms"] == pytest.approx(60)

    def test_a_cheap_sort_is_ignored(self):
        sort = node("Sort", total_time_ms=5, children=[node("Seq Scan", total_time_ms=3)])
        assert check_expensive_sort(plan_of(sort), T) == []

    def test_time_spent_reading_the_input_is_not_blamed_on_the_sort(self):
        sort = node("Sort", total_time_ms=100, children=[node("Seq Scan", total_time_ms=95)])
        assert check_expensive_sort(plan_of(sort), T) == []

    def test_other_node_types_are_ignored(self):
        assert check_expensive_sort(plan_of(node("Seq Scan", total_time_ms=500)), T) == []


class TestNestedLoopCost:
    def _loop(self, rows, total_ms, node_type="Nested Loop"):
        outer = node("Seq Scan", relation_name="users", actual_rows=1000, total_time_ms=5)
        inner = node("Index Scan", relation_name="orders", actual_loops=1000, total_time_ms=300)
        return node(node_type, actual_rows=rows, total_time_ms=total_ms, children=[outer, inner])

    def test_flags_many_rows_and_significant_time(self):
        issues = check_nested_loop_cost(plan_of(self._loop(40_000, 430)), T)

        assert len(issues) == 1
        assert issues[0].metrics["rows_produced"] == 40_000
        assert issues[0].metrics["inner_loops"] == 1000

    def test_a_small_nested_loop_is_fine(self):
        assert check_nested_loop_cost(plan_of(self._loop(50, 0.5)), T) == []

    def test_many_rows_but_fast_is_fine(self):
        assert check_nested_loop_cost(plan_of(self._loop(40_000, 2)), T) == []

    def test_slow_but_few_rows_is_fine(self):
        assert check_nested_loop_cost(plan_of(self._loop(100, 500)), T) == []

    def test_other_join_types_are_not_reported(self):
        assert check_nested_loop_cost(plan_of(self._loop(40_000, 430, "Hash Join")), T) == []


class TestEngine:
    def test_collects_issues_from_every_rule(self):
        scan = node("Seq Scan", relation_name="users", filter_condition="((city)::text = 'Mumbai'::text)",
                    plan_rows=1000, actual_rows=1012, rows_removed_by_filter=8988, total_time_ms=1.85)

        issues = run_rules(plan_of(scan, execution_time_ms=1.95))

        assert {i.rule_id for i in issues} == {"LARGE_SEQ_SCAN", "SEQ_SCAN_WITH_FILTER"}

    def test_a_healthy_plan_has_no_issues(self):
        scan = node("Index Scan", relation_name="users", index_name="users_pkey",
                    plan_rows=1, actual_rows=1, total_time_ms=0.03)
        assert run_rules(plan_of(scan, execution_time_ms=0.05)) == []

    def test_thresholds_are_configurable(self):
        scan = node("Seq Scan", relation_name="products", actual_rows=1000, total_time_ms=0.2)
        plan = plan_of(scan, execution_time_ms=0.3)

        assert run_rules(plan) == []
        flagged = run_rules(plan, AnalyzerThresholds(seq_scan_min_rows=500))
        assert [i.rule_id for i in flagged] == ["LARGE_SEQ_SCAN"]

    def test_thresholds_cannot_be_changed_by_accident(self):
        with pytest.raises(FrozenInstanceError):
            T.seq_scan_min_rows = 1
