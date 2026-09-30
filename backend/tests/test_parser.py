import pytest

from app.analyzer.parser import InvalidPlanError, own_time_ms, parse_plan, walk
from tests.factories import node, raw_plan_join, raw_plan_seq_scan


def test_parses_top_level_timings_and_root_node():
    plan = parse_plan(raw_plan_seq_scan())

    assert plan.planning_time_ms == pytest.approx(0.08)
    assert plan.execution_time_ms == pytest.approx(1.95)
    assert plan.rows_returned == 1012
    assert plan.root.node_type == "Seq Scan"
    assert plan.root.relation_name == "users"


def test_parses_scan_details():
    root = parse_plan(raw_plan_seq_scan()).root

    assert root.plan_rows == 1000
    assert root.actual_rows == 1012
    assert root.rows_removed_by_filter == 8988
    assert root.filter_condition == "((city)::text = 'Mumbai'::text)"
    assert root.shared_hit_blocks == 84
    assert root.shared_read_blocks == 0
    assert root.children == []


def test_parses_a_nested_join_plan_as_a_tree():
    root = parse_plan(raw_plan_join()).root

    assert root.node_type == "Hash Join"
    assert [child.node_type for child in root.children] == ["Seq Scan", "Hash"]
    hash_node = root.children[1]
    assert hash_node.children[0].node_type == "Seq Scan"
    assert hash_node.children[0].relation_name == "users"


def test_walk_visits_every_node_parent_first():
    root = parse_plan(raw_plan_join()).root
    assert [n.node_type for n in walk(root)] == ["Hash Join", "Seq Scan", "Hash", "Seq Scan"]


def test_total_time_is_per_loop_time_multiplied_by_loops():
    raw = [
        {
            "Plan": {
                "Node Type": "Index Scan",
                "Actual Rows": 40,
                "Actual Loops": 1000,
                "Actual Total Time": 0.3,
            },
            "Execution Time": 305.0,
        }
    ]
    root = parse_plan(raw).root
    assert root.actual_total_time == pytest.approx(0.3)
    assert root.total_time_ms == pytest.approx(300.0)


def test_missing_optional_fields_get_safe_defaults():
    raw = [{"Plan": {"Node Type": "Result"}, "Execution Time": 0.1}]
    root = parse_plan(raw).root

    assert root.relation_name is None
    assert root.filter_condition is None
    assert root.actual_rows == 0
    assert root.actual_loops == 1
    assert root.children == []


def test_unknown_node_types_still_parse():
    raw = [{"Plan": {"Node Type": "Gather Merge", "Actual Rows": 5}, "Execution Time": 1.0}]
    assert parse_plan(raw).root.node_type == "Gather Merge"


@pytest.mark.parametrize(
    "bad_plan",
    [
        None,
        {},
        [],
        "text",
        ["not a dict"],
        [{}],
        [{"Plan": {"Node Type": "Seq Scan"}}],  # no "Execution Time", so ANALYZE was not used
    ],
)
def test_malformed_plans_raise_a_clear_error(bad_plan):
    with pytest.raises(InvalidPlanError):
        parse_plan(bad_plan)


def test_own_time_excludes_children():
    parent = node("Hash Join", total_time_ms=100, children=[
        node("Seq Scan", total_time_ms=30),
        node("Hash", total_time_ms=20),
    ])
    assert own_time_ms(parent) == pytest.approx(50)


def test_own_time_is_never_negative():
    parent = node("Sort", total_time_ms=10, children=[node("Seq Scan", total_time_ms=12)])
    assert own_time_ms(parent) == 0
