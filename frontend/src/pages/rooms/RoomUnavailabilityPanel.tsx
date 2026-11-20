import { useCallback, useState } from "react";
import type { FormEvent } from "react";
import { useFetch } from "../../hooks/useFetch";
import { roomsApi } from "../../api/resources";
import { getErrorMessage } from "../../api/client";
import { DAY_NAMES } from "../../api/types";
import { Button, ErrorState, LoadingState, SelectField, TextField } from "../../components/ui";

interface RoomUnavailabilityPanelProps {
  roomId: number;
  readOnly?: boolean;
}

const dayOptions = DAY_NAMES.map((name, idx) => ({ value: idx, label: name }));

export function RoomUnavailabilityPanel({ roomId, readOnly }: RoomUnavailabilityPanelProps) {
  const listFetcher = useCallback(() => roomsApi.listUnavailability(roomId), [roomId]);
  const { data, loading, error, reload } = useFetch(listFetcher, [roomId]);

  const [dayIndex, setDayIndex] = useState("0");
  const [periodIndex, setPeriodIndex] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [rowError, setRowError] = useState<string | null>(null);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setRowError(null);
    try {
      await roomsApi.addUnavailability(roomId, {
        day_index: Number(dayIndex),
        period_index: periodIndex ? Number(periodIndex) : null,
      });
      setPeriodIndex("");
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
      await roomsApi.removeUnavailability(roomId, rowId);
      reload();
    } catch (err) {
      setRowError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-md border border-slate-200 p-3 dark:border-slate-700">
      <p className="mb-2 text-sm font-semibold text-slate-800 dark:text-slate-100">Unavailability</p>
      <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">
        Block out days (or specific periods) when this room cannot be scheduled.
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
                {DAY_NAMES[row.day_index]}
                {row.period_index !== null ? ` · period ${row.period_index}` : " · whole day"}
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
            <li className="text-sm text-slate-400 dark:text-slate-500">No unavailability set.</li>
          )}
        </ul>
      )}

      {!readOnly && (
        <form onSubmit={handleAdd} className="flex items-end gap-2">
          <SelectField
            label="Day"
            options={dayOptions}
            value={dayIndex}
            onChange={(e) => setDayIndex(e.target.value)}
            containerClassName="flex-1"
          />
          <TextField
            label="Period (optional)"
            type="number"
            min={0}
            value={periodIndex}
            onChange={(e) => setPeriodIndex(e.target.value)}
            placeholder="Whole day"
            containerClassName="w-36"
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
