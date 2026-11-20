import { useCallback, useState } from "react";
import type { FormEvent } from "react";
import { useFetch } from "../../hooks/useFetch";
import { teachersApi } from "../../api/resources";
import { getErrorMessage } from "../../api/client";
import { DAY_NAMES, PREFERENCE_TYPES, type PreferenceType } from "../../api/types";
import { Button, ErrorState, LoadingState, SelectField, TextField } from "../../components/ui";

interface TeacherPreferencesPanelProps {
  teacherId: number;
  readOnly?: boolean;
}

const dayOptions = DAY_NAMES.map((name, idx) => ({ value: idx, label: name }));
const preferenceOptions = PREFERENCE_TYPES.map((p) => ({ value: p, label: p.replace(/_/g, " ") }));

const needsDay = (t: string) => t === "preferred_day" || t === "free_day";

export function TeacherPreferencesPanel({ teacherId, readOnly }: TeacherPreferencesPanelProps) {
  const listFetcher = useCallback(() => teachersApi.listPreferences(teacherId), [teacherId]);
  const { data, loading, error, reload } = useFetch(listFetcher, [teacherId]);

  const [preferenceType, setPreferenceType] = useState<string>("preferred_day");
  const [dayIndex, setDayIndex] = useState("0");
  const [weight, setWeight] = useState("1");
  const [submitting, setSubmitting] = useState(false);
  const [rowError, setRowError] = useState<string | null>(null);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setRowError(null);
    try {
      await teachersApi.addPreference(teacherId, {
        preference_type: preferenceType as PreferenceType,
        day_index: needsDay(preferenceType) ? Number(dayIndex) : null,
        weight: Number(weight) || 1,
      });
      reload();
    } catch (err) {
      setRowError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRemove(rowId: number) {
    setSubmitting(true);
    try {
      await teachersApi.removePreference(teacherId, rowId);
      reload();
    } catch (err) {
      setRowError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-md border border-slate-200 p-3 dark:border-slate-700">
      <p className="mb-2 text-sm font-semibold text-slate-800 dark:text-slate-100">Preferences</p>
      <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
        Soft preferences the solver tries to honor, weighted by importance.
      </p>

      {loading && <LoadingState label="Loading…" />}
      {error && <ErrorState message={error} />}

      {!loading && !error && (
        <ul className="mb-3 space-y-1.5">
          {(data ?? []).map((row) => (
            <li
              key={row.id}
              className="flex items-center justify-between rounded-md bg-slate-50 px-2.5 py-1.5 text-sm dark:bg-slate-800"
            >
              <span>
                {row.preference_type.replace(/_/g, " ")}
                {row.day_index !== null ? ` · ${DAY_NAMES[row.day_index]}` : ""}
                <span className="text-slate-400"> · weight {row.weight}</span>
              </span>
              {!readOnly && (
                <button
                  type="button"
                  onClick={() => handleRemove(row.id)}
                  className="text-xs font-medium text-rose-600 hover:underline dark:text-rose-400"
                >
                  Remove
                </button>
              )}
            </li>
          ))}
          {(data ?? []).length === 0 && (
            <li className="text-sm text-slate-400 dark:text-slate-500">No preferences set.</li>
          )}
        </ul>
      )}

      {!readOnly && (
        <form onSubmit={handleAdd} className="flex flex-wrap items-end gap-2">
          <SelectField
            label="Preference"
            options={preferenceOptions}
            value={preferenceType}
            onChange={(e) => setPreferenceType(e.target.value)}
            containerClassName="min-w-[10rem] flex-1"
          />
          {needsDay(preferenceType) && (
            <SelectField
              label="Day"
              options={dayOptions}
              value={dayIndex}
              onChange={(e) => setDayIndex(e.target.value)}
              containerClassName="w-28"
            />
          )}
          <TextField
            label="Weight"
            type="number"
            min={0}
            step="0.5"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            containerClassName="w-24"
          />
          <Button type="submit" size="sm" variant="primary" disabled={submitting}>
            Add
          </Button>
        </form>
      )}
      {rowError && <p className="mt-2 text-xs font-medium text-rose-600 dark:text-rose-400">{rowError}</p>}
    </div>
  );
}
