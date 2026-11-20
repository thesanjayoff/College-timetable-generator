import { useState } from "react";
import type { DiagnosisFindingOut } from "../../api/types";
import { Badge, Card, EmptyState } from "../../components/ui";

/** Shared findings renderer for solve prechecks and the full diagnostics page. */
export function FindingsList({ findings }: { findings: DiagnosisFindingOut[] }) {
  if (findings.length === 0) {
    return <EmptyState title="No issues found" description="Prechecks did not flag anything blocking or worth a warning." />;
  }
  return (
    <div className="flex flex-col gap-3">
      {findings.map((f, i) => (
        <FindingRow key={i} finding={f} />
      ))}
    </div>
  );
}

function FindingRow({ finding }: { finding: DiagnosisFindingOut }) {
  const [showDetails, setShowDetails] = useState(false);
  const hasDetails = finding.details && Object.keys(finding.details).length > 0;
  return (
    <Card className="px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={finding.severity === "blocking" ? "rose" : "amber"}>{finding.severity}</Badge>
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {finding.category.replace(/_/g, " ")}
        </span>
      </div>
      <p className="mt-2 text-sm text-slate-800 dark:text-slate-100">{finding.message}</p>
      {finding.suggestions.length > 0 && (
        <ul className="mt-2 list-inside list-disc space-y-0.5 text-sm text-slate-600 dark:text-slate-300">
          {finding.suggestions.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ul>
      )}
      {hasDetails && (
        <div className="mt-2">
          <button
            type="button"
            className="text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400"
            onClick={() => setShowDetails((v) => !v)}
          >
            {showDetails ? "Hide details" : "Show details"}
          </button>
          {showDetails && (
            <pre className="mt-1.5 max-h-48 overflow-auto rounded-md bg-slate-50 p-2 text-xs text-slate-600 dark:bg-slate-800/60 dark:text-slate-300">
              {JSON.stringify(finding.details, null, 2)}
            </pre>
          )}
        </div>
      )}
    </Card>
  );
}
