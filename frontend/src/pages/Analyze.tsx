import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import QueryEditor from "../components/QueryEditor";
import ResultView from "../components/ResultView";
import { analyzeQuery } from "../services/api";
import type { AnalyzeResult } from "../types";

const SAMPLE_QUERY = "SELECT *\nFROM users\nWHERE city = 'Mumbai';";

export default function Analyze() {
  const location = useLocation();
  const prefilled = (location.state as { query?: string } | null)?.query;

  const [query, setQuery] = useState(prefilled ?? SAMPLE_QUERY);
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleAnalyze() {
    if (loading || !query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await analyzeQuery(query));
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      <section>
        <h1 className="text-2xl font-bold">Analyze PostgreSQL Query</h1>
        <p className="mt-1 mb-4 text-sm text-slate-500">
          Understand where performance problems come from. Only read-only SELECT queries are
          supported. The query is run with EXPLAIN ANALYZE inside a read-only transaction.
        </p>
        <QueryEditor
          value={query}
          onChange={setQuery}
          onSubmit={handleAnalyze}
          loading={loading}
        />
      </section>

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800
                     dark:border-red-900 dark:bg-red-950 dark:text-red-300"
        >
          <div className="font-semibold">Unable to analyze query.</div>
          <div className="mt-1">{error}</div>
        </div>
      )}

      {result && (
        <>
          {result.analysis_id !== null && (
            <p className="text-sm text-slate-500">
              Saved to history as{" "}
              <Link className="text-blue-600 underline" to={`/analysis/${result.analysis_id}`}>
                analysis #{result.analysis_id}
              </Link>
              .
            </p>
          )}
          <ResultView result={result} />
        </>
      )}
    </div>
  );
}
