import { useState } from "react";
import type { Issue, PlanNode } from "../types";
import { formatMs } from "../utils/format";

function ownTimeMs(node: PlanNode): number {
  const childrenTime = node.children.reduce((sum, child) => sum + child.total_time_ms, 0);
  return Math.max(node.total_time_ms - childrenTime, 0);
}

// Full class names are written out so Tailwind can find them at build time.
function heatStyle(share: number) {
  if (share >= 0.5) {
    return { card: "border-l-red-500", bar: "bg-red-500", label: "text-red-600 dark:text-red-400" };
  }
  if (share >= 0.2) {
    return { card: "border-l-orange-500", bar: "bg-orange-500", label: "text-orange-600 dark:text-orange-400" };
  }
  return { card: "border-l-slate-300 dark:border-l-slate-700", bar: "bg-slate-400", label: "text-slate-500" };
}

interface NodeViewProps {
  node: PlanNode;
  totalMs: number;
  issues: Issue[];
}

function NodeView({ node, totalMs, issues }: NodeViewProps) {
  const [open, setOpen] = useState(true);
  const own = ownTimeMs(node);
  const share = totalMs > 0 ? own / totalMs : 0;
  const heat = heatStyle(share);

  const nodeIssues = issues.filter(
    (issue) => issue.node_type === node.node_type && issue.relation_name === node.relation_name
  );

  const totalRows = node.actual_rows * Math.max(node.actual_loops, 1);

  return (
    <li>
      <div
        className={`rounded-lg border border-l-4 border-slate-200 bg-white p-3
                    dark:border-slate-800 dark:bg-slate-900 ${heat.card}`}
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="font-semibold">
            {node.children.length > 0 && (
              <button
                onClick={() => setOpen(!open)}
                className="mr-2 text-xs text-slate-500"
                aria-label={open ? "Collapse children" : "Expand children"}
              >
                {open ? "▼" : "▶"}
              </button>
            )}
            {node.node_type}
            {node.relation_name && (
              <span className="ml-2 font-mono text-sm font-normal text-slate-500">
                {node.relation_name}
              </span>
            )}
            {node.index_name && (
              <span className="ml-2 font-mono text-xs font-normal text-slate-500">
                via {node.index_name}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {nodeIssues.length > 0 && (
              <span className="rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-800 dark:bg-orange-950 dark:text-orange-300">
                ⚠ {nodeIssues.length} {nodeIssues.length === 1 ? "issue" : "issues"}
              </span>
            )}
            <span className={`text-sm font-medium ${heat.label}`}>
              {formatMs(own)} ms · {(share * 100).toFixed(0)}%
            </span>
          </div>
        </div>

        <div className="mt-2 h-1.5 w-full rounded bg-slate-200 dark:bg-slate-800">
          <div
            className={`h-1.5 rounded ${heat.bar}`}
            style={{ width: `${Math.min(share * 100, 100)}%` }}
          />
        </div>

        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
          <span>
            rows: {totalRows.toLocaleString()} actual / {node.plan_rows.toLocaleString()} estimated
          </span>
          {node.actual_loops > 1 && <span>loops: {node.actual_loops.toLocaleString()}</span>}
          {node.rows_removed_by_filter > 0 && (
            <span>filtered out: {node.rows_removed_by_filter.toLocaleString()} per loop</span>
          )}
          <span>
            buffers: {node.shared_hit_blocks.toLocaleString()} hit /{" "}
            {node.shared_read_blocks.toLocaleString()} read
          </span>
        </div>

        {node.filter_condition && (
          <div className="mt-2 overflow-x-auto rounded bg-slate-100 px-2 py-1 font-mono text-xs dark:bg-slate-950">
            Filter: {node.filter_condition}
          </div>
        )}
      </div>

      {open && node.children.length > 0 && (
        <ul className="ml-4 mt-2 space-y-2 border-l border-slate-300 pl-4 dark:border-slate-700">
          {node.children.map((child, index) => (
            <NodeView key={`${child.node_type}-${index}`} node={child} totalMs={totalMs} issues={issues} />
          ))}
        </ul>
      )}
    </li>
  );
}

interface PlanTreeProps {
  plan: PlanNode;
  executionTimeMs: number;
  issues: Issue[];
}

export default function PlanTree({ plan, executionTimeMs, issues }: PlanTreeProps) {
  return (
    <div>
      <ul>
        <NodeView node={plan} totalMs={executionTimeMs} issues={issues} />
      </ul>
      <p className="mt-3 text-xs text-slate-500">
        Time shown is each step's own time (excluding its children) and its share of the total
        execution time. Buffers are cumulative, so a parent's count includes its children's.
      </p>
    </div>
  );
}
