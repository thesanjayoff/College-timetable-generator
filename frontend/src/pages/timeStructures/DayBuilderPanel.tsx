import { useState } from "react";
import type { FormEvent } from "react";
import { timeStructuresApi } from "../../api/resources";
import { getErrorMessage } from "../../api/client";
import { DAY_NAMES } from "../../api/types";
import type { TimeStructureOut, WorkingDayOut } from "../../api/types";
import { Button, ErrorState, SelectField, TextField } from "../../components/ui";

interface DayBuilderPanelProps {
  timeStructure: TimeStructureOut;
  onChanged: () => void;
  readOnly?: boolean;
}

const emptyForm = { day_index: "1", name: "Mon", max_period_index: "" };

export function DayBuilderPanel({ timeStructure, onChanged, readOnly }: DayBuilderPanelProps) {
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [rowError, setRowError] = useState<string | null>(null);

  const days = [...timeStructure.days].sort((a, b) => a.day_index - b.day_index);
  const usedIndices = new Set(days.map((d) => d.day_index));
  const dayOptions = DAY_NAMES.map((name, idx) => ({ value: idx, label: name })).filter(
    (opt) => editingId !== null || !usedIndices.has(opt.value),
  );

  function startEdit(day: WorkingDayOut) {
    setEditingId(day.id);
    setForm({
      day_index: String(day.day_index),
      name: day.name,
      max_period_index: day.max_period_index !== null ? String(day.max_period_index) : "",
    });
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
    setSubmitting(true);
    setRowError(null);
    const payload = {
      day_index: Number(form.day_index),
      name: form.name,
      max_period_index: form.max_period_index ? Number(form.max_period_index) : null,
    };
    try {
      if (editingId) {
        await timeStructuresApi.updateDay(timeStructure.id, editingId, payload);
      } else {
        await timeStructuresApi.addDay(timeStructure.id, payload);
      }
      cancelEdit();
      onChanged();
    } catch (err) {
      setRowError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRemove(day: WorkingDayOut) {
    setSubmitting(true);
    try {
      await timeStructuresApi.removeDay(timeStructure.id, day.id);
      onChanged();
    } catch (err) {
      setRowError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-md border border-slate-200 p-3 dark:border-slate-700">
      <p className="mb-2 text-sm font-semibold text-slate-800 dark:text-slate-100">Working days</p>
      <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
        Which weekdays run classes, and an optional half-day cutoff (last period index taught that day).
      </p>

      <ul className="mb-3 space-y-1.5">
        {days.map((day) => (
          <li
            key={day.id}
            className="flex items-center justify-between rounded-md bg-slate-50 px-2.5 py-1.5 text-sm dark:bg-slate-800"
          >
            <span>
              <span className="font-medium">{DAY_NAMES[day.day_index]}</span> — {day.name}
              {day.max_period_index !== null && (
                <span className="text-slate-400"> · half day after period {day.max_period_index}</span>
              )}
            </span>
            {!readOnly && (
              <div className="flex gap-1.5">
                <button
                  type="button"
                  onClick={() => startEdit(day)}
                  className="text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                >
                  Edit
                </button>
                <button
                  type="button"
                  onClick={() => handleRemove(day)}
                  className="text-xs font-medium text-rose-600 hover:underline dark:text-rose-400"
                >
                  Remove
                </button>
              </div>
            )}
          </li>
        ))}
        {days.length === 0 && <li className="text-sm text-slate-400 dark:text-slate-500">No working days yet.</li>}
      </ul>

      {!readOnly && (
        <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-2">
          <SelectField
            label="Weekday"
            options={dayOptions}
            value={form.day_index}
            onChange={(e) =>
              setForm({ ...form, day_index: e.target.value, name: DAY_NAMES[Number(e.target.value)] ?? form.name })
            }
            containerClassName="w-32"
          />
          <TextField
            label="Display name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            containerClassName="flex-1 min-w-[8rem]"
          />
          <TextField
            label="Half-day cutoff period"
            type="number"
            min={0}
            value={form.max_period_index}
            onChange={(e) => setForm({ ...form, max_period_index: e.target.value })}
            placeholder="Full day"
            containerClassName="w-40"
          />
          <Button type="submit" size="sm" variant="primary" disabled={submitting}>
            {editingId ? "Update" : "Add day"}
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
