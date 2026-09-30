import type { CompareResult, MetricComparison, Verdict } from "../types";
import { formatMs } from "../utils/format";

// Full class names are written out so Tailwind can find them at build time.
const VERDICT_STYLES: Record<Verdict, { icon: string; box: string }> = {
  improved: {
    icon: "✅",
    box: "border-green-300 bg-green-50 text-green-900 dark:border-green-900 dark:bg-green-950 dark:text-green-200",
  },
  regressed: {
    icon: "⚠️",
    box: "border-red-300 bg-red-50 text-red-900 dark:border-red-900 dark:bg-red-950 dark:text-red-200",
  },
  no_significant_change: {
    icon: "➖",
    box: "border-slate-300 bg-slate-100 text-slate-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200",
  },
};

function formatValue(metric: MetricComparison, value: number): string {
  return metric.unit === "ms" ? `${formatMs(value)} ms` : Math.round(value).toLocaleString();
}

function formatChange(pct: number | null): string {
  if (pct === null) return "n/a";
  const rounded = Math.round(pct);
  if (rounded === 0) return "0%";
  return `${rounded > 0 ? "+" : ""}${rounded}%`;
}

function changeColor(better: boolean | null): string {
  if (better === true) return "font-semibold text-green-600 dark:text-green-400";
  if (better === false) return "font-semibold text-red-600 dark:text-red-400";
  return "text-slate-500";
}

export default function ComparisonTable({ result }: { result: CompareResult }) {
  const style = VERDICT_STYLES[result.verdict];

  return (
    <div className="space-y-4">
      <div className={`rounded-lg border p-4 ${style.box}`}>
        <div className="font-semibold">
          {style.icon} {result.summary}
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800">
              <th className="px-4 py-2">Metric</th>
              <th className="px-4 py-2 text-right">Before</th>
              <th className="px-4 py-2 text-right">After</th>
              <th className="px-4 py-2 text-right">Change</th>
            </tr>
          </thead>
          <tbody>
            {result.metrics.map((metric) => (
              <tr key={metric.key} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                <td className="px-4 py-2">{metric.label}</td>
                <td className="px-4 py-2 text-right font-mono">{formatValue(metric, metric.before)}</td>
                <td className="px-4 py-2 text-right font-mono">{formatValue(metric, metric.after)}</td>
                <td className={`px-4 py-2 text-right font-mono ${changeColor(metric.better)}`}>
                  {formatChange(metric.change_pct)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {(result.resolved_issues.length > 0 || result.new_issues.length > 0) && (
        <div className="grid gap-4 sm:grid-cols-2">
          {result.resolved_issues.length > 0 && (
            <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm dark:border-slate-800 dark:bg-slate-900">
              <div className="mb-1 font-semibold text-green-600 dark:text-green-400">No longer flagged</div>
              <ul className="list-disc pl-5">
                {result.resolved_issues.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}
          {result.new_issues.length > 0 && (
            <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm dark:border-slate-800 dark:bg-slate-900">
              <div className="mb-1 font-semibold text-red-600 dark:text-red-400">Newly flagged</div>
              <ul className="list-disc pl-5">
                {result.new_issues.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {result.notes.length > 0 && (
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600 dark:text-slate-400">
          {result.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}

      <p className="text-xs text-slate-500">
        These are measurements from this machine, not guarantees. Caching and system load affect
        timings.
      </p>
    </div>
  );
}
