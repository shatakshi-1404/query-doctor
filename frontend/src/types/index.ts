export type Severity = "info" | "warning" | "critical";

export interface PlanNode {
  node_type: string;
  relation_name: string | null;
  index_name: string | null;
  filter_condition: string | null;
  plan_rows: number;
  actual_rows: number;
  actual_loops: number;
  actual_total_time: number;
  total_time_ms: number;
  rows_removed_by_filter: number;
  shared_hit_blocks: number;
  shared_read_blocks: number;
  children: PlanNode[];
}

export interface Issue {
  rule_id: string;
  title: string;
  severity: Severity;
  node_type: string;
  relation_name: string | null;
  what_happened: string;
  why_it_matters: string;
  what_to_investigate: string;
  metrics: Record<string, unknown>;
}

export interface Recommendation {
  title: string;
  description: string;
  sql_suggestion: string | null;
  relation_name: string | null;
  related_rule_ids: string[];
}

export interface AnalyzeResult {
  query: string;
  planning_time_ms: number;
  execution_time_ms: number;
  rows_returned: number;
  plan: PlanNode;
  issues: Issue[];
  recommendations: Recommendation[];
  analysis_id: number | null;
  created_at: string | null;
}

export interface HistoryItem {
  analysis_id: number;
  query_text: string;
  planning_time_ms: number;
  execution_time_ms: number;
  rows_returned: number;
  issues_count: number;
  created_at: string;
}

export type Verdict = "improved" | "regressed" | "no_significant_change";

export interface MetricComparison {
  key: string;
  label: string;
  unit: string | null;
  before: number;
  after: number;
  change_pct: number | null;
  better: boolean | null;
}

export interface CompareResult {
  before: AnalyzeResult;
  after: AnalyzeResult;
  metrics: MetricComparison[];
  verdict: Verdict;
  summary: string;
  resolved_issues: string[];
  new_issues: string[];
  notes: string[];
  runs: number;
}
