import { useState } from "react";
import ComparisonTable from "../components/ComparisonTable";
import PlanTree from "../components/PlanTree";
import { compareQueries } from "../services/api";
import type { CompareResult } from "../types";

const EXAMPLES = [
  {
    label: "SELECT * vs 3 columns",
    before: "SELECT *\nFROM users\nWHERE city = 'Mumbai';",
    after: "SELECT id, name, email\nFROM users\nWHERE city = 'Mumbai';",
  },
  {
    label: "Sort all vs top 10",
    before: "SELECT *\nFROM orders\nORDER BY total DESC;",
    after: "SELECT *\nFROM orders\nORDER BY total DESC\nLIMIT 10;",
  },
  {
    label: "Full scan vs key range",
    before: "SELECT *\nFROM users\nWHERE city = 'Mumbai';",
    after: "SELECT *\nFROM users\nWHERE id < 100;",
  },
];

const TEXTAREA_CLASS =
  "w-full rounded-lg border border-slate-300 bg-white p-3 font-mono text-sm " +
  "focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 " +
  "dark:border-slate-700 dark:bg-slate-900";

export default function Compare() {
  const [before, setBefore] = useState(EXAMPLES[0].before);
  const [after, setAfter] = useState(EXAMPLES[0].after);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const canSubmit = !loading && before.trim() !== "" && after.trim() !== "";

  async function handleCompare() {
    if (!canSubmit) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await compareQueries(before, after));
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
        <h1 className="text-2xl font-bold">Compare Queries</h1>
        <p className="mt-1 mb-4 text-sm text-slate-500">
          Paste two versions of a query. Each is run several times and the median run is used, so
          a single slow run does not decide the result.
        </p>

        <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
          <span className="text-slate-500">Examples:</span>
          {EXAMPLES.map((example) => (
            <button
              key={example.label}
              onClick={() => {
                setBefore(example.before);
                setAfter(example.after);
              }}
              className="rounded-full border border-slate-300 px-3 py-1 hover:bg-slate-100
                         dark:border-slate-700 dark:hover:bg-slate-800"
            >
              {example.label}
            </button>
          ))}
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-semibold" htmlFor="before-query">
              Before
            </label>
            <textarea
              id="before-query"
              value={before}
              onChange={(e) => setBefore(e.target.value)}
              rows={7}
              maxLength={10000}
              spellCheck={false}
              className={TEXTAREA_CLASS}
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-semibold" htmlFor="after-query">
              After
            </label>
            <textarea
              id="after-query"
              value={after}
              onChange={(e) => setAfter(e.target.value)}
              rows={7}
              maxLength={10000}
              spellCheck={false}
              className={TEXTAREA_CLASS}
            />
          </div>
        </div>

        <div className="mt-3 flex justify-end">
          <button
            onClick={handleCompare}
            disabled={!canSubmit}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white
                       hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Comparing (3 runs each)..." : "Compare Queries"}
          </button>
        </div>
      </section>

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-red-300 bg-red-50 p-4 text-sm text-red-800
                     dark:border-red-900 dark:bg-red-950 dark:text-red-300"
        >
          <div className="font-semibold">Unable to compare queries.</div>
          <div className="mt-1">{error}</div>
        </div>
      )}

      {result && (
        <>
          <section>
            <h2 className="mb-3 text-lg font-semibold">Result</h2>
            <ComparisonTable result={result} />
          </section>

          <section>
            <h2 className="mb-3 text-lg font-semibold">Execution Plans</h2>
            <div className="grid gap-6 lg:grid-cols-2">
              <div>
                <h3 className="mb-2 text-sm font-semibold text-slate-500">Before</h3>
                <PlanTree
                  plan={result.before.plan}
                  executionTimeMs={result.before.execution_time_ms}
                  issues={result.before.issues}
                />
              </div>
              <div>
                <h3 className="mb-2 text-sm font-semibold text-slate-500">After</h3>
                <PlanTree
                  plan={result.after.plan}
                  executionTimeMs={result.after.execution_time_ms}
                  issues={result.after.issues}
                />
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
