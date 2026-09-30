from app.analyzer.parser import ParsedPlan, PlanNode
from app.schemas.analysis import AnalyzeResponse, IssueOut, PlanNodeOut


# ---------- Raw EXPLAIN JSON, shaped like PostgreSQL's real output ----------

def raw_plan_seq_scan(execution_time: float = 1.95) -> list[dict]:
    return [
        {
            "Plan": {
                "Node Type": "Seq Scan",
                "Relation Name": "users",
                "Plan Rows": 1000,
                "Actual Rows": 1012,
                "Actual Loops": 1,
                "Actual Total Time": 1.85,
                "Filter": "((city)::text = 'Mumbai'::text)",
                "Rows Removed by Filter": 8988,
                "Shared Hit Blocks": 84,
                "Shared Read Blocks": 0,
            },
            "Planning Time": 0.08,
            "Execution Time": execution_time,
        }
    ]


def raw_plan_join() -> list[dict]:
    return [
        {
            "Plan": {
                "Node Type": "Hash Join",
                "Plan Rows": 5000,
                "Actual Rows": 5061,
                "Actual Loops": 1,
                "Actual Total Time": 11.8,
                "Shared Hit Blocks": 200,
                "Shared Read Blocks": 0,
                "Plans": [
                    {
                        "Node Type": "Seq Scan",
                        "Relation Name": "orders",
                        "Plan Rows": 50000,
                        "Actual Rows": 50000,
                        "Actual Loops": 1,
                        "Actual Total Time": 4.1,
                        "Shared Hit Blocks": 100,
                        "Shared Read Blocks": 0,
                    },
                    {
                        "Node Type": "Hash",
                        "Plan Rows": 1000,
                        "Actual Rows": 1012,
                        "Actual Loops": 1,
                        "Actual Total Time": 1.6,
                        "Shared Hit Blocks": 90,
                        "Shared Read Blocks": 0,
                        "Plans": [
                            {
                                "Node Type": "Seq Scan",
                                "Relation Name": "users",
                                "Plan Rows": 1000,
                                "Actual Rows": 1012,
                                "Actual Loops": 1,
                                "Actual Total Time": 1.5,
                                "Filter": "((city)::text = 'Mumbai'::text)",
                                "Rows Removed by Filter": 8988,
                                "Shared Hit Blocks": 84,
                                "Shared Read Blocks": 0,
                            }
                        ],
                    },
                ],
            },
            "Planning Time": 0.35,
            "Execution Time": 12.4,
        }
    ]


def raw_plan(execution_time: float) -> list[dict]:
    """A minimal valid plan with a chosen execution time."""
    return [
        {
            "Plan": {
                "Node Type": "Result",
                "Actual Rows": 1,
                "Actual Loops": 1,
                "Actual Total Time": execution_time,
            },
            "Planning Time": 0.1,
            "Execution Time": execution_time,
        }
    ]


# ---------- Parsed objects, used to test the rules ----------

def node(node_type: str = "Seq Scan", **kwargs) -> PlanNode:
    return PlanNode(node_type=node_type, **kwargs)


def plan_of(root: PlanNode, execution_time_ms: float = 100.0) -> ParsedPlan:
    return ParsedPlan(
        root=root,
        planning_time_ms=0.1,
        execution_time_ms=execution_time_ms,
        rows_returned=root.actual_rows,
    )


# ---------- API-shaped objects, used to test comparison ----------

ISSUE_TITLES = {
    "LARGE_SEQ_SCAN": "Large Sequential Scan",
    "SEQ_SCAN_WITH_FILTER": "Filter Applied After Full Scan",
}


def make_issue(rule_id: str = "LARGE_SEQ_SCAN", relation: str = "users") -> IssueOut:
    return IssueOut(
        rule_id=rule_id,
        title=ISSUE_TITLES[rule_id],
        severity="warning",
        node_type="Seq Scan",
        relation_name=relation,
        what_happened="x",
        why_it_matters="y",
        what_to_investigate="z",
    )


def make_analysis(
    execution_ms: float,
    rows: int = 1000,
    node_type: str = "Seq Scan",
    relation: str = "users",
    issues: list[IssueOut] | None = None,
    planning_ms: float = 0.1,
    hits: int = 84,
    reads: int = 0,
) -> AnalyzeResponse:
    plan = PlanNodeOut(
        node_type=node_type,
        relation_name=relation,
        plan_rows=rows,
        actual_rows=rows,
        actual_loops=1,
        actual_total_time=execution_ms,
        total_time_ms=execution_ms,
        rows_removed_by_filter=0,
        shared_hit_blocks=hits,
        shared_read_blocks=reads,
    )
    return AnalyzeResponse(
        query="SELECT ...",
        planning_time_ms=planning_ms,
        execution_time_ms=execution_ms,
        rows_returned=rows,
        plan=plan,
        issues=issues or [],
        recommendations=[],
    )
