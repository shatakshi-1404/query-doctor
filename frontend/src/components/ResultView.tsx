import type { AnalyzeResult } from "../types";
import { formatMs } from "../utils/format";
import IssueCard from "./IssueCard";
import MetricCard from "./MetricCard";
import PlanTree from "./PlanTree";
import RecommendationCard from "./RecommendationCard";

export default function ResultView({ result }: { result: AnalyzeResult }) {
  return (
    <div className="space-y-8">
      <section>
        <h2 className="mb-3 text-lg font-semibold">Query Performance</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <MetricCard label="Execution" value={formatMs(result.execution_time_ms)} unit="ms" />
          <MetricCard label="Planning" value={formatMs(result.planning_time_ms)} unit="ms" />
          <MetricCard label="Rows Returned" value={result.rows_returned.toLocaleString()} />
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">Execution Plan</h2>
        <PlanTree
          plan={result.plan}
          executionTimeMs={result.execution_time_ms}
          issues={result.issues}
        />
      </section>

      <section>
        <h2 className="mb-3 text-lg font-semibold">
          Potential Issues{result.issues.length > 0 && ` (${result.issues.length})`}
        </h2>
        {result.issues.length === 0 ? (
          <p className="rounded-lg border border-slate-200 bg-white p-4 text-sm dark:border-slate-800 dark:bg-slate-900">
            ✅ No issues were flagged by the current rules. That does not guarantee the query is
            optimal, only that none of QueryDoctor's checks were triggered.
          </p>
        ) : (
          <div className="space-y-4">
            {result.issues.map((issue, index) => (
              <IssueCard key={`${issue.rule_id}-${index}`} issue={issue} />
            ))}
          </div>
        )}
      </section>

      {result.recommendations.length > 0 && (
        <section>
          <h2 className="mb-3 text-lg font-semibold">Recommendations</h2>
          <div className="space-y-4">
            {result.recommendations.map((rec, index) => (
              <RecommendationCard key={`${rec.title}-${index}`} recommendation={rec} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
