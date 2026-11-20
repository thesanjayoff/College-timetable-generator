import { useCallback, useState } from "react";
import { useFetch } from "../../hooks/useFetch";
import { solveApi } from "../../api/resources";
import { Button, ErrorState, LoadingState, PageHeader } from "../../components/ui";
import { useVersionIdParam, VersionPicker } from "../versions/VersionPicker";
import { FindingsList } from "./FindingsList";

export default function DiagnosticsPage() {
  const [versionId, setVersionId] = useVersionIdParam();
  const [runNonce, setRunNonce] = useState(0);

  const fetcher = useCallback(() => {
    if (versionId === null) return Promise.resolve(null);
    return solveApi.prechecks(versionId);
  }, [versionId, runNonce]);
  const { data: findings, loading, error } = useFetch(fetcher, [fetcher]);

  return (
    <div>
      <PageHeader
        title="Diagnostics"
        description="Infeasibility explanations and constraint diagnostics for a version, independent of running a full solve."
      />

      <div className="mb-5 flex flex-wrap items-end gap-3">
        <VersionPicker value={versionId} onChange={setVersionId} />
        <Button
          variant="primary"
          disabled={versionId === null || loading}
          onClick={() => setRunNonce((n) => n + 1)}
        >
          {loading ? "Running…" : "Run diagnostics"}
        </Button>
      </div>

      {versionId === null && (
        <p className="text-sm text-slate-500 dark:text-slate-400">Select a version to run diagnostics against.</p>
      )}
      {loading && <LoadingState />}
      {error && <ErrorState message={error} />}
      {!loading && !error && findings && <FindingsList findings={findings} />}
    </div>
  );
}
