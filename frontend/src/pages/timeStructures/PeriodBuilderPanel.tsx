import { useState } from "react";
import type { FormEvent } from "react";
import { timeStructuresApi } from "../../api/resources";
import { getErrorMessage } from "../../api/client";
import { PERIOD_KINDS, type PeriodKind, type PeriodSlotOut, type TimeStructureOut } from "../../api/types";
import { Badge, Button, ErrorState, SelectField, TextField } from "../../components/ui";

interface PeriodBuilderPanelProps {
  timeStructure: TimeStructureOut;
  onChanged: () => void;
  readOnly?: boolean;
}

const kindOptions = PERIOD_KINDS.map((k) => ({ value: k, label: k }));
const kindTone: Record<PeriodKind, "indigo" | "slate" | "amber"> = {
  teaching: "indigo",
  break: "slate",
  lunch: "amber",
};

function nextDefaults(periods: PeriodSlotOut[]) {
  const last = [...periods].sort((a, b) => a.period_index - b.period_index).at(-1);
  const nextIndex = last ? last.period_index + 1 : 0;
  return { period_index: String(nextIndex), label: `P${nextIndex + 1}`, start_time: "", end_time: "" };
}

export function PeriodBuilderPanel({ timeStructure, onChanged, readOnly }: PeriodBuilderPanelProps) {
  const periods = [...timeStructure.periods].sort((a, b) => a.period_index - b.period_index);

  const [form, setForm] = useState(() => ({ ...nextDefaults(periods), kind: "teaching" as string, teaching_order: "" }));
  const [editingId, setEditingId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [rowError, setRowError] = useState<string | null>(null);

  function startEdit(period: PeriodSlotOut) {
    setEditingId(period.id);
    setForm({
      period_index: String(period.period_index),
      label: period.label,
      start_time: period.start_time,
      end_time: period.end_time,
      kind: period.kind,
      teaching_order: period.teaching_order !== null ? String(period.teaching_order) : "",
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setForm({ ...nextDefaults(periods), kind: "teaching", teaching_order: "" });
    setRowError(null);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!form.label.trim() || !form.start_time.trim() || !form.end_time.trim()) {
      setRowError("Label, start time and end time are required");
      return;
    }
    setSubmitting(true);
    setRowError(null);
    const payload = {
      period_index: Number(form.period_index),
      label: form.label,
      start_time: form.start_time,
      end_time: form.end_time,
      kind: form.kind as PeriodKind,
      teaching_order: form.teaching_order ? Number(form.teaching_order) : null,
    };
    try {
      if (editingId) {
        await timeStructuresApi.updatePeriod(timeStructure.id, editingId, payload);
      } else {
        await timeStructuresApi.addPeriod(timeStructure.id, payload);
      }
      cancelEdit();
      onChanged();
    } catch (err) {
      setRowError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRemove(period: PeriodSlotOut) {
    setSubmitting(true);
    try {
      await timeStructuresApi.removePeriod(timeStructure.id, period.id);
      onChanged();
    } catch (err) {
      setRowError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-md border border-slate-200 p-3 dark:border-slate-700">
      <p className="mb-2 text-sm font-semibold text-slate-800 dark:text-slate-100">Period slots</p>
      <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
        The periods that make up a day, in order, including breaks and lunch.
      </p>

      <ul className="mb-3 space-y-1.5">
        {periods.map((period) => (
          <li
            key={period.id}
            className="flex items-center justify-between rounded-md bg-slate-50 px-2.5 py-1.5 text-sm dark:bg-slate-800"
          >
            <span className="flex items-center gap-2">
              <span className="font-mono text-xs text-slate-400">#{period.period_index}</span>
              <span className="font-medium">{period.label}</span>
              <span className="text-slate-400">
                {period.start_time}–{period.end_time}
              </span>
              <Badge tone={kindTone[period.kind]}>{period.kind}</Badge>
            </span>
            {!readOnly && (
              <div className="flex gap-1.5">
                <button
                  type="button"
                  onClick={() => startEdit(period)}
                  className="text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                >
                  Edit
                </button>
                <button
                  type="button"
                  onClick={() => handleRemove(period)}
                  className="text-xs font-medium text-rose-600 hover:underline dark:text-rose-400"
                >
                  Remove
                </button>
              </div>
            )}
          </li>
        ))}
        {periods.length === 0 && <li className="text-sm text-slate-400 dark:text-slate-500">No periods yet.</li>}
      </ul>

      {!readOnly && (
        <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-2">
          <TextField
            label="Index"
            type="number"
            min={0}
            value={form.period_index}
            onChange={(e) => setForm({ ...form, period_index: e.target.value })}
            containerClassName="w-20"
          />
          <TextField
            label="Label"
            value={form.label}
            onChange={(e) => setForm({ ...form, label: e.target.value })}
            containerClassName="w-24"
          />
          <TextField
            label="Start"
            type="time"
            value={form.start_time}
            onChange={(e) => setForm({ ...form, start_time: e.target.value })}
            containerClassName="w-32"
          />
          <TextField
            label="End"
            type="time"
            value={form.end_time}
            onChange={(e) => setForm({ ...form, end_time: e.target.value })}
            containerClassName="w-32"
          />
          <SelectField
            label="Kind"
            options={kindOptions}
            value={form.kind}
            onChange={(e) => setForm({ ...form, kind: e.target.value })}
            containerClassName="w-32"
          />
          <TextField
            label="Teaching order"
            type="number"
            min={0}
            value={form.teaching_order}
            onChange={(e) => setForm({ ...form, teaching_order: e.target.value })}
            placeholder="auto"
            containerClassName="w-28"
            hint="Optional"
          />
          <Button type="submit" size="sm" variant="primary" disabled={submitting}>
            {editingId ? "Update" : "Add period"}
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
