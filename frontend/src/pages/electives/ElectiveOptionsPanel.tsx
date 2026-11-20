import { useCallback, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useFetch } from "../../hooks/useFetch";
import { electivesApi, subjectsApi, teachersApi } from "../../api/resources";
import { getErrorMessage } from "../../api/client";
import { ROOM_TYPES, type ElectiveOptionOut, type RoomType } from "../../api/types";
import { Button, ErrorState, LoadingState, SelectField, TextField } from "../../components/ui";

interface ElectiveOptionsPanelProps {
  basketId: number;
  readOnly?: boolean;
}

const roomTypeOptions = ROOM_TYPES.map((t) => ({ value: t, label: t.replace("_", " ") }));

function emptyForm() {
  return { subject_id: "", teacher_id: "", room_type_required: "classroom" as string, expected_strength: "30" };
}

export function ElectiveOptionsPanel({ basketId, readOnly }: ElectiveOptionsPanelProps) {
  const listFetcher = useCallback(() => electivesApi.listOptions(basketId), [basketId]);
  const { data, loading, error, reload } = useFetch(listFetcher, [basketId]);
  const { data: subjects } = useFetch(subjectsApi.list, []);
  const { data: teachers } = useFetch(teachersApi.list, []);

  const [form, setForm] = useState(emptyForm());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [rowError, setRowError] = useState<string | null>(null);

  const subjectOptions = useMemo(() => (subjects ?? []).map((s) => ({ value: s.id, label: `${s.code} — ${s.name}` })), [subjects]);
  const teacherOptions = useMemo(() => (teachers ?? []).map((t) => ({ value: t.id, label: `${t.code} — ${t.name}` })), [teachers]);
  const subjectName = useCallback((id: number) => subjects?.find((s) => s.id === id)?.name ?? `#${id}`, [subjects]);
  const teacherName = useCallback((id: number | null) => (id ? teachers?.find((t) => t.id === id)?.name ?? `#${id}` : "—"), [teachers]);

  function startEdit(opt: ElectiveOptionOut) {
    setEditingId(opt.id);
    setForm({
      subject_id: String(opt.subject_id),
      teacher_id: opt.teacher_id ? String(opt.teacher_id) : "",
      room_type_required: opt.room_type_required,
      expected_strength: String(opt.expected_strength),
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(emptyForm());
    setRowError(null);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!form.subject_id) {
      setRowError("Subject is required");
      return;
    }
    setSubmitting(true);
    setRowError(null);
    const payload = {
      subject_id: Number(form.subject_id),
      teacher_id: form.teacher_id ? Number(form.teacher_id) : null,
      room_type_required: form.room_type_required as RoomType,
      expected_strength: Number(form.expected_strength) || 30,
    };
    try {
      if (editingId) {
        await electivesApi.updateOption(basketId, editingId, payload);
      } else {
        await electivesApi.createOption(basketId, payload);
      }
      cancelEdit();
      reload();
    } catch (err) {
      setRowError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRemove(opt: ElectiveOptionOut) {
    setSubmitting(true);
    try {
      await electivesApi.removeOption(basketId, opt.id);
      reload();
    } catch (err) {
      setRowError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-md border border-slate-200 p-3 dark:border-slate-700">
      <p className="mb-2 text-sm font-semibold text-slate-800 dark:text-slate-100">Options</p>
      <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
        The subjects students can choose from within this basket.
      </p>

      {loading && <LoadingState label="Loading…" />}
      {error && <ErrorState message={error} />}

      {!loading && !error && (
        <ul className="mb-3 space-y-1.5">
          {(data ?? []).map((opt) => (
            <li key={opt.id} className="flex items-center justify-between rounded-md bg-slate-50 px-2.5 py-1.5 text-sm dark:bg-slate-800">
              <span>
                {subjectName(opt.subject_id)}
                <span className="text-slate-400"> · {teacherName(opt.teacher_id)} · {opt.room_type_required.replace("_", " ")} · ~{opt.expected_strength}</span>
              </span>
              {!readOnly && (
                <div className="flex gap-1.5">
                  <button type="button" onClick={() => startEdit(opt)} className="text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400">
                    Edit
                  </button>
                  <button type="button" onClick={() => handleRemove(opt)} className="text-xs font-medium text-rose-600 hover:underline dark:text-rose-400">
                    Remove
                  </button>
                </div>
              )}
            </li>
          ))}
          {(data ?? []).length === 0 && <li className="text-sm text-slate-400 dark:text-slate-500">No options yet.</li>}
        </ul>
      )}

      {!readOnly && (
        <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-2">
          <SelectField
            label="Subject"
            options={subjectOptions}
            placeholder="Select subject"
            value={form.subject_id}
            onChange={(e) => setForm({ ...form, subject_id: e.target.value })}
            containerClassName="min-w-[10rem] flex-1"
          />
          <SelectField
            label="Teacher"
            options={teacherOptions}
            placeholder="Unassigned"
            value={form.teacher_id}
            onChange={(e) => setForm({ ...form, teacher_id: e.target.value })}
            containerClassName="min-w-[10rem] flex-1"
          />
          <SelectField
            label="Room type"
            options={roomTypeOptions}
            value={form.room_type_required}
            onChange={(e) => setForm({ ...form, room_type_required: e.target.value })}
            containerClassName="w-36"
          />
          <TextField
            label="Expected strength"
            type="number"
            min={1}
            value={form.expected_strength}
            onChange={(e) => setForm({ ...form, expected_strength: e.target.value })}
            containerClassName="w-32"
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
      {rowError && <ErrorState message={rowError} />}
    </div>
  );
}
