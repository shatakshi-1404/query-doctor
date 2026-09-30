import type { Issue, Severity } from "../types";

// Full class names are written out so Tailwind can find them at build time.
const SEVERITY_STYLES: Record<Severity, { icon: string; label: string; border: string; badge: string }> = {
  info: {
    icon: "🔵",
    label: "Info",
    border: "border-l-blue-500",
    badge: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
  },
  warning: {
    icon: "🟠",
    label: "Warning",
    border: "border-l-orange-500",
    badge: "bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300",
  },
  critical: {
    icon: "🔴",
    label: "Critical",
    border: "border-l-red-500",
    badge: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  },
};

function Section({ heading, text }: { heading: string; text: string }) {
  return (
    <div className="mt-3">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{heading}</div>
      <p className="mt-1 text-sm">{text}</p>
    </div>
  );
}

export default function IssueCard({ issue }: { issue: Issue }) {
  const style = SEVERITY_STYLES[issue.severity] ?? SEVERITY_STYLES.warning;

  return (
    <div
      className={`rounded-lg border border-l-4 border-slate-200 bg-white p-4
                  dark:border-slate-800 dark:bg-slate-900 ${style.border}`}
    >
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-semibold">
          {style.icon} {issue.title}
          {issue.relation_name && (
            <span className="ml-2 font-mono text-sm font-normal text-slate-500">
              {issue.relation_name}
            </span>
          )}
        </h3>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${style.badge}`}>
          {style.label}
        </span>
      </div>
      <Section heading="What happened" text={issue.what_happened} />
      <Section heading="Why it might matter" text={issue.why_it_matters} />
      <Section heading="What to investigate" text={issue.what_to_investigate} />
    </div>
  );
}
