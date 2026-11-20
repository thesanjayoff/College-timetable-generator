import { useCallback, useState } from "react";
import type { FormEvent } from "react";
import { useFetch } from "../../hooks/useFetch";
import { sectionsApi } from "../../api/resources";
import { getErrorMessage } from "../../api/client";
import type { LabBatchOut } from "../../api/types";
import { Button, ErrorState, LoadingState, TextField } from "../../components/ui";

interface LabBatchesPanelProps {
  sectionId: number;
  readOnly?: boolean;
}

const emptyForm = { name: "", strength: "30" };

/** Inline management of a section's lab batches, embedded in the section edit drawer. */
export function LabBatchesPanel({ sectionId, readOnly }: LabBatchesPanelProps) {
  const listFetcher = useCallback(() => sectionsApi.listLabBatches(sectionId), [sectionId]);
  const { data, loading, error, reload } = useFetch(listFetcher, [sectionId]);

  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [rowError, setRowError] = useState<string | null>(null);

  function startEdit(batch: LabBatchOut) {
    setEditingId(batch.id);
    setForm({ name: batch.name, strength: String(batch.strength) });
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(emptyForm);
    setRowError(null);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) {
      setRowError("Name is required");
      return;
    }
    const strength = Number(form.strength);
    if (!strength || strength <= 0) {
      setRowError("Strength must be a positive number");
      return;
    }
    setSubmitting(true);
    setRowError(null);
    try {
      if (editingId) {
        await sectionsApi.updateLabBatch(sectionId, editingId, { name: form.name, strength });
      } else {
        await sectionsApi.createLabBatch(sectionId, { name: form.name, strength });
      }
      setForm(emptyForm);
      setEditingId(null);
      reload();
    } catch (err) {
      setRowError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRemove(batch: LabBatchOut) {
    setSubmitting(true);
    try {
      await sectionsApi.removeLabBatch(sectionId, batch.id);
      reload();
    } catch (err) {
      setRowError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-md border border-slate-200 p-3 dark:border-slate-700">
      <p className="mb-2 text-sm font-semibold text-slate-800 dark:text-slate-100">Lab batches</p>
      <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
        Split this section into smaller batches for lab sessions (e.g. B1, B2, B3).
      </p>

      {loading && <LoadingState label="Loading batches…" />}
      {error && <ErrorState message={error} />}

      {!loading && !error && (
        <ul className="mb-3 space-y-1.5">
          {(data ?? []).map((batch) => (
            <li
              key={batch.id}
              className="flex items-center justify-between rounded-md bg-slate-50 px-2.5 py-1.5 text-sm dark:bg-slate-800"
            >
              <span>
                {batch.name} <span className="text-slate-400">· strength {batch.strength}</span>
              </span>
              {!readOnly && (
                <div className="flex gap-1.5">
                  <button
                    type="button"
                    onClick={() => startEdit(batch)}
                    className="text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => handleRemove(batch)}
                    className="text-xs font-medium text-rose-600 hover:underline dark:text-rose-400"
                  >
                    Remove
                  </button>
                </div>
              )}
            </li>
          ))}
          {(data ?? []).length === 0 && (
            <li className="text-sm text-slate-400 dark:text-slate-500">No lab batches yet.</li>
          )}
        </ul>
      )}

      {!readOnly && (
        <form onSubmit={handleSubmit} className="flex items-end gap-2">
          <TextField
            label="Batch name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="B1"
            containerClassName="flex-1"
          />
          <TextField
            label="Strength"
            type="number"
            min={1}
            value={form.strength}
            onChange={(e) => setForm({ ...form, strength: e.target.value })}
            containerClassName="w-28"
          />
          <Button type="submit" size="sm" variant="primary" disabled={submitting}>
            {editingId ? "Update" : "Add"}
          </Button>
          {editingId && (
            <Button type="button" size="sm" variant="ghost" onClick={cancelEdit}>
              Cancel
            </Button>
          )}
        </form>
      )}
      {rowError && <p className="mt-2 text-xs font-medium text-rose-600 dark:text-rose-400">{rowError}</p>}
    </div>
  );
}
