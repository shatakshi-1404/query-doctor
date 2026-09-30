import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getHistory } from "../services/api";
import type { HistoryItem } from "../types";
import { formatDateTime, formatMs } from "../utils/format";

function preview(sql: string): string {
  const oneLine = sql.replace(/\s+/g, " ").trim();
  return oneLine.length > 110 ? `${oneLine.slice(0, 110)}...` : oneLine;
}

export default function History() {
  const [items, setItems] = useState<HistoryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getHistory()
      .then((data) => {
        if (!cancelled) setItems(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Something went wrong.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold">Recent Queries</h1>
      <p className="mt-1 mb-4 text-sm text-slate-500">
        Every successful analysis is saved. Click one to reopen it.
      </p>

      {error && (
        <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          {error}
        </div>
      )}

      {!error && items === null && <p className="text-sm text-slate-500">Loading...</p>}

      {items !== null && items.length === 0 && (
        <p className="rounded-lg border border-slate-200 bg-white p-4 text-sm dark:border-slate-800 dark:bg-slate-900">
          No analyses yet. Run one from the Analyze page.
        </p>
      )}

      {items !== null && items.length > 0 && (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={item.analysis_id}>
              <Link
                to={`/analysis/${item.analysis_id}`}
                className="block rounded-lg border border-slate-200 bg-white p-4 hover:border-blue-500
                           dark:border-slate-800 dark:bg-slate-900 dark:hover:border-blue-500"
              >
                <div className="font-mono text-sm">{preview(item.query_text)}</div>
                <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-500">
                  <span className="font-medium text-slate-700 dark:text-slate-300">
                    {formatMs(item.execution_time_ms)} ms
                  </span>
                  <span>{item.rows_returned.toLocaleString()} rows</span>
                  <span>
                    {item.issues_count === 0
                      ? "no issues"
                      : `${item.issues_count} ${item.issues_count === 1 ? "issue" : "issues"}`}
                  </span>
                  <span>{formatDateTime(item.created_at)}</span>
                  <span>#{item.analysis_id}</span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
