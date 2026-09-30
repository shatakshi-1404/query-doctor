import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import ResultView from "../components/ResultView";
import { getAnalysis } from "../services/api";
import type { AnalyzeResult } from "../types";
import { formatDateTime } from "../utils/format";

export default function AnalysisDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setResult(null);
    setError(null);
    getAnalysis(Number(id))
      .then((data) => {
        if (!cancelled) setResult(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Something went wrong.");
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <div className="space-y-6">
      <Link to="/history" className="text-sm text-blue-600 underline">
        ← Back to history
      </Link>

      {error && (
        <div role="alert" className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          {error}
        </div>
      )}

      {!error && !result && <p className="text-sm text-slate-500">Loading...</p>}

      {result && (
        <>
          <section>
            <h1 className="text-2xl font-bold">Analysis #{result.analysis_id}</h1>
            {result.created_at && (
              <p className="mt-1 text-sm text-slate-500">
                Analyzed on {formatDateTime(result.created_at)}. These numbers are a snapshot
                and will differ if you run the query again.
              </p>
            )}
            <pre className="mt-3 overflow-x-auto rounded-lg border border-slate-200 bg-white p-3 font-mono text-sm dark:border-slate-800 dark:bg-slate-900">
              {result.query}
            </pre>
            <button
              onClick={() => navigate("/", { state: { query: result.query } })}
              className="mt-3 rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium
                         hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
            >
              Open in editor
            </button>
          </section>
          <ResultView result={result} />
        </>
      )}
    </div>
  );
}
