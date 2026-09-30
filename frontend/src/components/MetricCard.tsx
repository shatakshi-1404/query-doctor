interface MetricCardProps {
  label: string;
  value: string;
  unit?: string;
}

export default function MetricCard({ label, value, unit }: MetricCardProps) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold">
        {value}
        {unit && <span className="ml-1 text-base font-normal text-slate-500">{unit}</span>}
      </div>
    </div>
  );
}
