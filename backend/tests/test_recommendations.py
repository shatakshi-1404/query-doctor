import pytest

from app.analyzer.engine import run_rules
from app.analyzer.recommendations import _index_candidate, build_recommendations
from tests.factories import node, plan_of

MUMBAI_FILTER = "((city)::text = 'Mumbai'::text)"


def mumbai_scan(**overrides):
    values = dict(relation_name="users", filter_condition=MUMBAI_FILTER, plan_rows=1000,
                  actual_rows=1012, rows_removed_by_filter=8988, total_time_ms=1.85)
    values.update(overrides)
    return node("Seq Scan", **values)


class TestIndexCandidate:
    def test_single_equality_column(self):
        columns, statement = _index_candidate("users", MUMBAI_FILTER)
        assert columns == ["city"]
        assert statement == "CREATE INDEX idx_users_city\nON users(city);"

    def test_simple_unqualified_comparison(self):
        columns, _ = _index_candidate("order_items", "(quantity = 5)")
        assert columns == ["quantity"]

    def test_equality_columns_come_before_range_columns(self):
        flt = "(((status)::text = 'paid'::text) AND (total > '5000'::numeric))"
        columns, statement = _index_candidate("orders", flt)
        assert columns == ["status", "total"]
        assert "idx_orders_status_total" in statement

    def test_ordering_holds_even_when_the_range_comes_first(self):
        columns, _ = _index_candidate("orders", "((total > 5000) AND (status = 1))")
        assert columns == ["status", "total"]

    @pytest.mark.parametrize(
        "relation, filter_text",
        [
            ("orders", "(((status)::text = 'paid'::text) OR (total > 5000))"),   # OR
            ("users", "(lower((email)::text) = 'a@b.com'::text)"),               # function on a column
            ("users", "((name)::text ~~ '%abc%'::text)"),                        # LIKE pattern
            ("orders", "((status)::text <> 'x'::text)"),                         # not-equal only
            ("Users; DROP", "(city = 'x')"),                                     # unsafe table name
            ("users", None),                                                     # no filter at all
            (None, "(city = 'x')"),                                              # no table name
        ],
    )
    def test_no_statement_when_it_cannot_be_done_safely(self, relation, filter_text):
        assert _index_candidate(relation, filter_text) is None

    def test_index_names_respect_the_postgresql_length_limit(self):
        _, statement = _index_candidate("a" * 50, "(some_column = 1)")
        index_name = statement.split()[2]
        assert len(index_name) <= 63


class TestBuildRecommendations:
    def test_no_issues_means_no_recommendations(self):
        assert build_recommendations([]) == []

    def test_scan_issues_are_merged_into_one_index_recommendation(self):
        issues = run_rules(plan_of(mumbai_scan(), execution_time_ms=1.95))
        assert {i.rule_id for i in issues} == {"LARGE_SEQ_SCAN", "SEQ_SCAN_WITH_FILTER"}

        recs = build_recommendations(issues)

        assert len(recs) == 1
        rec = recs[0]
        assert rec.title == "Consider an index on users(city)"
        assert "CREATE INDEX idx_users_city" in rec.sql_suggestion
        assert set(rec.related_rule_ids) == {"SEQ_SCAN_WITH_FILTER", "LARGE_SEQ_SCAN"}

    def test_index_advice_is_hedged_not_promised(self):
        issues = run_rules(plan_of(mumbai_scan(), execution_time_ms=1.95))
        description = build_recommendations(issues)[0].description
        assert "Potential index candidate" in description
        assert "re-analyze" in description

    def test_unsafe_filter_gives_advice_but_no_sql(self):
        scan = mumbai_scan(filter_condition="(((city)::text = 'a'::text) OR (id > 5))")
        recs = build_recommendations(run_rules(plan_of(scan, execution_time_ms=1.95)))

        assert len(recs) == 1
        assert recs[0].sql_suggestion is None
        assert recs[0].title.startswith("Review indexes for the filter on")

    def test_large_scan_without_a_filter_gets_general_advice(self):
        scan = node("Seq Scan", relation_name="orders", plan_rows=50_000, actual_rows=50_000,
                    total_time_ms=4.0)
        recs = build_recommendations(run_rules(plan_of(scan, execution_time_ms=5.0)))

        assert [r.title for r in recs] == ["Reduce the rows read from orders"]
        assert recs[0].sql_suggestion is None

    def test_estimate_mismatch_suggests_analyze_once_per_table(self):
        left = node("Seq Scan", relation_name="orders", plan_rows=100, actual_rows=50_000, total_time_ms=2)
        right = node("Seq Scan", relation_name="orders", plan_rows=100, actual_rows=50_000, total_time_ms=2)
        join = node("Nested Loop", plan_rows=1, actual_rows=1, total_time_ms=5, children=[left, right])

        recs = build_recommendations(run_rules(plan_of(join, execution_time_ms=10)))

        stats = [r for r in recs if r.title == "Check table statistics"]
        assert len(stats) == 1
        assert stats[0].sql_suggestion == "ANALYZE orders;"

    def test_a_slow_sort_gets_one_recommendation_not_two(self):
        scan = node("Seq Scan", relation_name="orders", total_time_ms=30)
        sort = node("Sort", actual_rows=50_000, total_time_ms=90, children=[scan])

        issues = run_rules(plan_of(sort, execution_time_ms=100))
        assert {"EXPENSIVE_SORT", "HIGH_ACTUAL_TIME"} <= {i.rule_id for i in issues}

        recs = build_recommendations(issues)
        assert [r.title for r in recs] == ["Reduce the cost of sorting"]

    def test_a_bottleneck_with_no_more_specific_issue_is_reported_on_its_own(self):
        agg = node("Aggregate", total_time_ms=95)
        recs = build_recommendations(run_rules(plan_of(agg, execution_time_ms=100)))
        assert [r.title for r in recs] == ["Start with the Aggregate step"]

    def test_nested_loop_recommendation_mentions_join_indexes(self):
        outer = node("Seq Scan", relation_name="users", plan_rows=1000, actual_rows=1000, total_time_ms=5)
        inner = node("Index Scan", relation_name="orders", plan_rows=40, actual_rows=40,
                     actual_loops=1000, total_time_ms=300)
        loop = node("Nested Loop", plan_rows=40_000, actual_rows=40_000, total_time_ms=430,
                    children=[outer, inner])

        recs = build_recommendations(run_rules(plan_of(loop, execution_time_ms=432)))

        assert "Check indexes on the join columns" in [r.title for r in recs]

    def test_recommendations_are_deterministic(self):
        plan = plan_of(mumbai_scan(), execution_time_ms=1.95)
        first = build_recommendations(run_rules(plan))
        second = build_recommendations(run_rules(plan))
        assert first == second
