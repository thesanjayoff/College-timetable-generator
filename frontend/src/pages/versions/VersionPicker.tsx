import { useSearchParams } from "react-router-dom";
import { useCallback, useMemo } from "react";
import { useFetch } from "../../hooks/useFetch";
import { versionsApi } from "../../api/resources";
import type { VersionOut } from "../../api/types";
import { Badge, SelectField } from "../../components/ui";
import { statusTone } from "./versionStatus";

/**
 * Keeps the selected version id in sync with the `?version=` URL query param, so
 * navigating between Solve / Diagnostics / Substitution / Import-Export keeps context.
 */
export function useVersionIdParam(): [number | null, (id: number | null) => void] {
  const [params, setParams] = useSearchParams();
  const raw = params.get("version");
  const versionId = raw ? Number(raw) : null;

  const setVersionId = useCallback(
    (id: number | null) => {
      setParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (id === null) next.delete("version");
          else next.set("version", String(id));
          return next;
        },
        { replace: true },
      );
    },
    [setParams],
  );

  return [versionId && !Number.isNaN(versionId) ? versionId : null, setVersionId];
}

interface VersionPickerProps {
  value: number | null;
  onChange: (versionId: number | null) => void;
  label?: string;
  hint?: string;
  excludeId?: number;
}

/** Reusable version dropdown shared by the Solve / Diagnostics / Substitution / Import-Export pages. */
export function VersionPicker({ value, onChange, label = "Version", hint, excludeId }: VersionPickerProps) {
  const { data: versions, loading, error } = useFetch(versionsApi.list, []);

  const options = useMemo(
    () =>
      (versions ?? [])
        .filter((v) => v.id !== excludeId)
        .map((v) => ({ value: v.id, label: `#${v.id} — ${v.name} (${v.status})` })),
    [versions, excludeId],
  );

  return (
    <div>
      <SelectField
        label={label}
        hint={error ? undefined : hint}
        placeholder={loading ? "Loading versions…" : "Select a version"}
        options={options}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
      />
      {error && <p className="mt-1 text-xs font-medium text-rose-600 dark:text-rose-400">{error}</p>}
    </div>
  );
}

export function VersionStatusBadge({ version }: { version: VersionOut }) {
  return <Badge tone={statusTone(version.status)}>{version.status}</Badge>;
}
