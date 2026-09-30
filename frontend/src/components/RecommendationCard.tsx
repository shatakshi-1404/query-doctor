import { useState } from "react";
import type { Recommendation } from "../types";

export default function RecommendationCard({ recommendation }: { recommendation: Recommendation }) {
  const [copied, setCopied] = useState(false);

  async function copySql() {
    if (!recommendation.sql_suggestion) return;
    try {
      await navigator.clipboard.writeText(recommendation.sql_suggestion);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard access can be blocked by the browser; the SQL is still selectable.
    }
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <h3 className="font-semibold">💡 {recommendation.title}</h3>
      <p className="mt-2 text-sm">{recommendation.description}</p>

      {recommendation.sql_suggestion && (
        <div className="relative mt-3">
          <pre className="overflow-x-auto rounded-md bg-slate-100 p-3 font-mono text-sm dark:bg-slate-950">
            {recommendation.sql_suggestion}
          </pre>
          <button
            onClick={copySql}
            className="absolute right-2 top-2 rounded border border-slate-300 bg-white px-2 py-0.5
                       text-xs dark:border-slate-700 dark:bg-slate-900"
          >
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      )}
    </div>
  );
}
