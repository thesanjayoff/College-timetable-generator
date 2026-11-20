import { useCallback, useMemo, useState } from "react";
import { useFetch } from "../../hooks/useFetch";
import { subjectsApi, teachersApi } from "../../api/resources";
import { getErrorMessage } from "../../api/client";
import { Button, ErrorState, LoadingState, SelectField } from "../../components/ui";

interface TeacherSubjectsPanelProps {
  teacherId: number;
  readOnly?: boolean;
}

export function TeacherSubjectsPanel({ teacherId, readOnly }: TeacherSubjectsPanelProps) {
  const listFetcher = useCallback(() => teachersApi.listSubjects(teacherId), [teacherId]);
  const { data, loading, error, reload } = useFetch(listFetcher, [teacherId]);
  const { data: subjects } = useFetch(subjectsApi.list, []);

  const [selected, setSelected] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [rowError, setRowError] = useState<string | null>(null);

  const subjectName = useCallback(
    (id: number) => {
      const s = subjects?.find((x) => x.id === id);
      return s ? `${s.code} — ${s.name}` : `#${id}`;
    },
    [subjects],
  );

  const availableOptions = useMemo(() => {
    const usedIds = new Set((data ?? []).map((link) => link.subject_id));
    return (subjects ?? [])
      .filter((s) => !usedIds.has(s.id))
      .map((s) => ({ value: s.id, label: `${s.code} — ${s.name}` }));
  }, [subjects, data]);

  async function handleAdd() {
    if (!selected) return;
    setSubmitting(true);
    setRowError(null);
    try {
      await teachersApi.addSubject(teacherId, { subject_id: Number(selected) });
      setSelected("");
      reload();
    } catch (err) {
      setRowError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRemove(linkId: number) {
    setSubmitting(true);
    try {
      await teachersApi.removeSubject(teacherId, linkId);
      reload();
    } catch (err) {
      setRowError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-md border border-slate-200 p-3 dark:border-slate-700">
      <p className="mb-2 text-sm font-semibold text-slate-800 dark:text-slate-100">Eligible subjects</p>
      <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
        Subjects this teacher is qualified to be assigned to.
      </p>

      {loading && <LoadingState label="Loading…" />}
      {error && <ErrorState message={error} />}

      {!loading && !error && (
        <ul className="mb-3 space-y-1.5">
          {(data ?? []).map((link) => (
            <li
              key={link.id}
              className="flex items-center justify-between rounded-md bg-slate-50 px-2.5 py-1.5 text-sm dark:bg-slate-800"
            >
              <span>{subjectName(link.subject_id)}</span>
              {!readOnly && (
                <button
                  type="button"
                  onClick={() => handleRemove(link.id)}
                  className="text-xs font-medium text-rose-600 hover:underline dark:text-rose-400"
                >
                  Remove
                </button>
              )}
            </li>
          ))}
          {(data ?? []).length === 0 && (
            <li className="text-sm text-slate-400 dark:text-slate-500">No subjects assigned yet.</li>
          )}
        </ul>
      )}

      {!readOnly && (
        <div className="flex items-end gap-2">
          <SelectField
            label="Add subject"
            options={availableOptions}
            placeholder="Select a subject"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            containerClassName="flex-1"
          />
          <Button size="sm" variant="primary" disabled={!selected || submitting} onClick={handleAdd}>
            Add
          </Button>
        </div>
      )}
      {rowError && <p className="mt-2 text-xs font-medium text-rose-600 dark:text-rose-400">{rowError}</p>}
    </div>
  );
}
