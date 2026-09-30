from dataclasses import dataclass, field
from typing import Any, Iterator


class InvalidPlanError(Exception):
    """The plan returned by PostgreSQL does not have the expected structure."""


@dataclass
class PlanNode:
    node_type: str
    relation_name: str | None = None
    index_name: str | None = None
    filter_condition: str | None = None
    plan_rows: int = 0            # the planner's estimate
    actual_rows: int = 0          # real rows, per loop
    actual_loops: int = 1
    actual_total_time: float = 0.0  # ms, per loop
    total_time_ms: float = 0.0      # actual_total_time * loops
    rows_removed_by_filter: int = 0
    shared_hit_blocks: int = 0
    shared_read_blocks: int = 0
    children: list["PlanNode"] = field(default_factory=list)


@dataclass
class ParsedPlan:
    root: PlanNode
    planning_time_ms: float
    execution_time_ms: float
    rows_returned: int


def parse_node(raw: dict[str, Any]) -> PlanNode:
    loops = raw.get("Actual Loops", 1)
    actual_time = raw.get("Actual Total Time", 0.0)

    return PlanNode(
        node_type=raw.get("Node Type", "Unknown"),
        relation_name=raw.get("Relation Name"),
        index_name=raw.get("Index Name"),
        filter_condition=raw.get("Filter"),
        plan_rows=raw.get("Plan Rows", 0),
        actual_rows=raw.get("Actual Rows", 0),
        actual_loops=loops,
        actual_total_time=actual_time,
        total_time_ms=actual_time * loops,
        rows_removed_by_filter=raw.get("Rows Removed by Filter", 0),
        shared_hit_blocks=raw.get("Shared Hit Blocks", 0),
        shared_read_blocks=raw.get("Shared Read Blocks", 0),
        children=[parse_node(child) for child in raw.get("Plans", [])],
    )


def parse_plan(raw_plan: Any) -> ParsedPlan:
    """Convert PostgreSQL's EXPLAIN (FORMAT JSON) output into a ParsedPlan."""
    if not isinstance(raw_plan, list) or not raw_plan:
        raise InvalidPlanError("Plan is empty or not a list.")

    top = raw_plan[0]
    if not isinstance(top, dict) or "Plan" not in top:
        raise InvalidPlanError("Plan is missing the 'Plan' section.")
    if "Execution Time" not in top:
        raise InvalidPlanError("Plan has no timing data (was ANALYZE used?).")

    root = parse_node(top["Plan"])

    return ParsedPlan(
        root=root,
        planning_time_ms=top.get("Planning Time", 0.0),
        execution_time_ms=top["Execution Time"],
        rows_returned=root.actual_rows,
    )


def walk(node: PlanNode) -> Iterator[PlanNode]:
    """Yield a node and all of its descendants (parent first)."""
    yield node
    for child in node.children:
        yield from walk(child)


def own_time_ms(node: PlanNode) -> float:
    """Time spent in this node itself, excluding its children."""
    children_time = sum(child.total_time_ms for child in node.children)
    return max(node.total_time_ms - children_time, 0.0)
