import { useCallback, useMemo, useState } from "react";
import { useFetch } from "../../hooks/useFetch";
import { substitutionApi, teachersApi } from "../../api/resources";
import { DAY_NAMES } from "../../api/types";
import { Badge, Button, Card, EmptyState, ErrorState, LoadingState, PageHeader, SelectField } from "../../components/ui";
import { useVersionIdParam, VersionPicker } from "../versions/VersionPicker";

export default function SubstitutionPlannerPage() {
  const [versionId, setVersionId] = useVersionIdParam();
  const { data: teachers } = useFetch(teachersApi.list, []);

  const [teacherId, setTeacherId] = useState<string>("");
  const [dayIndex, setDayIndex] = useState<string>("1");
  const [searchNonce, setSearchNonce] = useState(0);

  const teacherOptions = useMemo(() => (teachers ?? []).map((t) => ({ value: t.id, label: `${t.code} — ${t.name}` })), [teachers]);
  const dayOptions = useMemo(() => DAY_NAMES.map((name, idx) => ({ value: idx, label: name })), []);

  const fetcher = useCallback(() => {
    if (versionId === null || !teacherId || searchNonce === 0) return Promise.resolve(null);
    return substitutionApi.plan(versionId, Number(teacherId), Number(dayIndex));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [versionId, teacherId, dayIndex, searchNonce]);
  const { data: plan, loading, error } = useFetch(fetcher, [fetcher]);

  const teacherName = (id: number) => teachers?.find((t) => t.id === id)?.name ?? `#${id}`;

  return (
    <div>
      <PageHeader
        title="Substitution Planner"
        description="Find eligible, free replacement teachers for a specific teacher's sessions on a given day, ranked by lowest current workload first."
      />

      <div className="mb-5 flex flex-wrap items-end gap-3">
        <div className="w-64">
          <VersionPicker value={versionId} onChange={setVersionId} />
        </div>
        <SelectField
          label="Absent teacher"
          options={teacherOptions}
          placeholder="Select a teacher"
          value={teacherId}
          onChange={(e) => setTeacherId(e.target.value)}
          containerClassName="w-64"
        />
        <SelectField
          label="Day"
          options={dayOptions}
          value={dayIndex}
          onChange={(e) => setDayIndex(e.target.value)}
          containerClassName="w-40"
        />
        <Button
          variant="primary"
          disabled={versionId === null || !teacherId || loading}
          onClick={() => setSearchNonce((n) => n + 1)}
        >
          {loading ? "Searching…" : "Find substitutes"}
        </Button>
      </div>

      {error && <ErrorState message={error} />}
      {loading && <LoadingState />}

      {!loading && !error && plan && plan.length === 0 && (
        <EmptyState
          title="No sessions found"
          description="This teacher has no sessions scheduled on the selected day in this version."
        />
      )}

      {!loading && !error && plan && plan.length > 0 && (
        <div className="flex flex-col gap-4">
          {plan.map((session) => (
            <Card key={session.session_id} className="px-4 py-3">
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                Session #{session.session_id} · {DAY_NAMES[session.day_index] ?? `Day ${session.day_index}`} · period{" "}
                {session.period_index + 1}
                {session.num_periods > 1 ? `–${session.period_index + session.num_periods}` : ""}
              </p>
              {session.candidates.length === 0 ? (
                <p className="mt-2 text-sm text-amber-600 dark:text-amber-400">
                  No eligible, free substitute teacher was found for this session.
                </p>
              ) : (
                <ul className="mt-2 flex flex-col gap-1.5">
                  {session.candidates.map((c, idx) => (
                    <li
                      key={c.teacher_id}
                      className={`flex items-center justify-between rounded-md px-3 py-1.5 text-sm ${
                        idx === 0
                          ? "bg-emerald-50 dark:bg-emerald-950/40"
                          : "bg-slate-50 dark:bg-slate-800/60"
                      }`}
                    >
                      <span className="flex items-center gap-2">
                        {c.name || teacherName(c.teacher_id)}
                        {idx === 0 && <Badge tone="green">best fit</Badge>}
                      </span>
                      <span className="text-slate-500 dark:text-slate-400">{c.current_weekly_load} periods/week</span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
