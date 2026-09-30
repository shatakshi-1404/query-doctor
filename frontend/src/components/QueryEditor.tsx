interface QueryEditorProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  loading: boolean;
}

const MAX_LENGTH = 10000;

export default function QueryEditor({ value, onChange, onSubmit, loading }: QueryEditorProps) {
  return (
    <div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if ((e.ctrlKey || e.metaKey) && e.key === "Enter") onSubmit();
        }}
        rows={7}
        maxLength={MAX_LENGTH}
        spellCheck={false}
        placeholder="SELECT * FROM users WHERE city = 'Mumbai';"
        className="w-full rounded-lg border border-slate-300 bg-white p-3 font-mono text-sm
                   focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500
                   dark:border-slate-700 dark:bg-slate-900"
      />
      <div className="mt-3 flex items-center justify-between">
        <span className="text-xs text-slate-500">
          Ctrl + Enter to analyze · {value.length.toLocaleString()} / {MAX_LENGTH.toLocaleString()}
        </span>
        <button
          onClick={onSubmit}
          disabled={loading || !value.trim()}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white
                     hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Analyzing..." : "Analyze Query"}
        </button>
      </div>
    </div>
  );
}
