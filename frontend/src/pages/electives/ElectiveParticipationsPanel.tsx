import { useCallback, useMemo, useState } from "react";
import { useFetch } from "../../hooks/useFetch";
import { electivesApi, sectionsApi } from "../../api/resources";
import { getErrorMessage } from "../../api/client";
import { Button, ErrorState, LoadingState, SelectField } from "../../components/ui";

interface ElectiveParticipationsPanelProps {
  basketId: number;
  readOnly?: boolean;
}

export function ElectiveParticipationsPanel({ basketId, readOnly }: ElectiveParticipationsPanelProps) {
  const listFetcher = useCallback(() => electivesApi.listParticipations(basketId), [basketId]);
  const { data, loading, error, reload } = useFetch(listFetcher, [basketId]);
  const { data: sections } = useFetch(sectionsApi.list, []);

  const [selected, setSelected] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [rowError, setRowError] = useState<string | null>(null);

  const sectionName = useCallback((id: number) => sections?.find((s) => s.id === id)?.name ?? `#${id}`, [sections]);

  const availableOptions = useMemo(() => {
    const usedIds = new Set((data ?? []).map((p) => p.section_id));
    return (sections ?? []).filter((s) => !usedIds.has(s.id)).map((s) => ({ value: s.id, label: s.name }));
  }, [sections, data]);

  async function handleAdd() {
    if (!selected) return;
    setSubmitting(true);
    setRowError(null);
    try {
      await electivesApi.createParticipation(basketId, { section_id: Number(selected) });
      setSelected("");
      reload();
    } catch (err) {
      setRowError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRemove(id: number) {
    setSubmitting(true);
    try {
      await electivesApi.removeParticipation(basketId, id);
      reload();
    } catch (err) {
      setRowError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-md border border-slate-200 p-3 dark:border-slate-700">
      <p className="mb-2 text-sm font-semibold text-slate-800 dark:text-slate-100">Participating sections</p>
      <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">Sections whose students pick from this basket.</p>

      {loading && <LoadingState label="Loading…" />}
      {error && <ErrorState message={error} />}

      {!loading && !error && (
        <ul className="mb-3 space-y-1.5">
          {(data ?? []).map((p) => (
            <li key={p.id} className="flex items-center justify-between rounded-md bg-slate-50 px-2.5 py-1.5 text-sm dark:bg-slate-800">
              <span>{sectionName(p.section_id)}</span>
              {!readOnly && (
                <button type="button" onClick={() => handleRemove(p.id)} className="text-xs font-medium text-rose-600 hover:underline dark:text-rose-400">
                  Remove
                </button>
              )}
            </li>
          ))}
          {(data ?? []).length === 0 && <li className="text-sm text-slate-400 dark:text-slate-500">No sections yet.</li>}
        </ul>
      )}

      {!readOnly && (
        <div className="flex items-end gap-2">
          <SelectField
            label="Add section"
            options={availableOptions}
            placeholder="Select a section"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            containerClassName="flex-1"
          />
          <Button size="sm" variant="primary" disabled={!selected || submitting} onClick={handleAdd}>
            Add
          </Button>
        </div>
      )}
      {rowError && <ErrorState message={rowError} />}
    </div>
  );
}
