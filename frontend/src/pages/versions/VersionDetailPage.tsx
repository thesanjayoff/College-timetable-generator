import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import { useFetch } from "../../hooks/useFetch";
import {
  roomsApi,
  sectionsApi,
  teachersApi,
  timeStructuresApi,
  versionsApi,
} from "../../api/resources";
import { getErrorMessage } from "../../api/client";
import { DAY_NAMES } from "../../api/types";
import type {
  PublishConflictOut,
  SlotSuggestionOut,
  TimetableSessionOut,
  VersionDiffEntryOut,
} from "../../api/types";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  SelectField,
} from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { statusTone } from "./versionStatus";
import { TimetableGrid } from "./TimetableGrid";
import type { GridDay, GridPeriod, ViewAxis } from "./TimetableGrid";

function extractDetailObject(err: unknown): Record<string, unknown> | null {
  if (axios.isAxiosError(err) && (err.response?.status === 409 || err.response?.status === 400)) {
    const detail = (err.response.data as { detail?: unknown } | undefined)?.detail;
    if (detail && typeof detail === "object" && !Array.isArray(detail)) {
      return detail as Record<string, unknown>;
    }
  }
  return null;
}

function formatTuple(t: [number, number, number | null] | undefined): string {
  if (!t) return "—";
  const [day, period, room] = t;
  return `${DAY_NAMES[day] ?? `Day ${day}`} · P${period + 1}${room !== null && room !== undefined ? ` · room #${room}` : ""}`;
}

export default function VersionDetailPage() {
  const { versionId: versionIdRaw } = useParams<{ versionId: string }>();
  const versionId = Number(versionIdRaw);
  const navigate = useNavigate();
  const { canWrite, isViewer } = useAuth();

  const { data: version, loading, error, reload } = useFetch(
    useCallback(() => versionsApi.get(versionId), [versionId]),
    [versionId],
  );
  const { data: unplaced, reload: reloadUnplaced } = useFetch(
    useCallback(() => versionsApi.listUnplaced(versionId), [versionId]),
    [versionId],
  );
  const { data: structures } = useFetch(timeStructuresApi.list, []);
  const { data: sections } = useFetch(sectionsApi.list, []);
  const { data: teachers } = useFetch(teachersApi.list, []);
  const { data: rooms } = useFetch(roomsApi.list, []);

  const [axis, setAxis] = useState<ViewAxis>("section");
  const [entityId, setEntityId] = useState<number | null>(null);
  const [selected, setSelected] = useState<TimetableSessionOut | null>(null);
  const [suggestions, setSuggestions] = useState<SlotSuggestionOut[] | null>(null);
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [banner, setBanner] = useState<{ tone: "error" | "success"; text: string } | null>(null);
  const [actionBusy, setActionBusy] = useState(false);
  const [publishConflict, setPublishConflict] = useState<PublishConflictOut | null>(null);
  const [compareToId, setCompareToId] = useState<string>("");
  const [showUnplaced, setShowUnplaced] = useState(false);

  const entityOptions = useMemo(() => {
    if (axis === "section") return (sections ?? []).map((s) => ({ value: s.id, label: s.name }));
    if (axis === "teacher") return (teachers ?? []).map((t) => ({ value: t.id, label: `${t.code} — ${t.name}` }));
    return (rooms ?? []).map((r) => ({ value: r.id, label: `${r.code} — ${r.name}` }));
  }, [axis, sections, teachers, rooms]);

  // Pick a default entity whenever the axis changes (or once its list loads).
  useEffect(() => {
    if (entityId !== null && entityOptions.some((o) => o.value === entityId)) return;
    setEntityId(entityOptions.length > 0 ? Number(entityOptions[0].value) : null);
    setSelected(null);
    setSuggestions(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [axis, entityOptions]);

  const sessionsFetcher = useCallback(() => {
    if (!versionId || entityId === null) return Promise.resolve([] as TimetableSessionOut[]);
    const params =
      axis === "section" ? { section_id: entityId } : axis === "teacher" ? { teacher_id: entityId } : { room_id: entityId };
    return versionsApi.listSessions(versionId, params);
  }, [versionId, axis, entityId]);
  const { data: sessions, loading: sessionsLoading, error: sessionsError, reload: reloadSessions } = useFetch(
    sessionsFetcher,
    [sessionsFetcher],
  );

  const sectionLabel = useCallback(
    (id: number) => sections?.find((s) => s.id === id)?.name ?? `#${id}`,
    [sections],
  );

  const structure = useMemo(() => {
    if (!structures || structures.length === 0) return undefined;
    return structures.find((s) => s.is_default) ?? structures[0];
  }, [structures]);

  // Builds grid axes from the time structure (for nice day names / period labels),
  // but ALWAYS unions in any day/period index that actually appears in the current
  // sessions -- a session must never be silently hidden just because the structure
  // the grid happens to be using doesn't declare that slot (e.g. a section using a
  // non-default structure, or a structure with gaps).
  const { days, periods } = useMemo<{ days: GridDay[]; periods: GridPeriod[] }>(() => {
    const dayMap = new Map<number, GridDay>();
    const periodMap = new Map<number, GridPeriod>();

    if (structure) {
      for (const day of structure.days) {
        dayMap.set(day.day_index, { day_index: day.day_index, name: day.name });
      }
      for (const period of structure.periods) {
        periodMap.set(period.period_index, {
          period_index: period.period_index,
          label: period.label,
          sublabel: `${period.start_time}–${period.end_time}`,
          isTeaching: period.kind === "teaching",
        });
      }
    }

    for (const s of sessions ?? []) {
      if (!dayMap.has(s.day_index)) {
        dayMap.set(s.day_index, { day_index: s.day_index, name: DAY_NAMES[s.day_index] ?? `Day ${s.day_index}` });
      }
      for (let k = 0; k < s.num_periods; k++) {
        const idx = s.period_index + k;
        if (!periodMap.has(idx)) {
          periodMap.set(idx, { period_index: idx, label: `P${idx + 1}`, isTeaching: true });
        }
      }
    }

    const d = Array.from(dayMap.values()).sort((a, b) => a.day_index - b.day_index);
    const p = Array.from(periodMap.values()).sort((a, b) => a.period_index - b.period_index);
    return { days: d, periods: p };
  }, [structure, sessions]);

  function refreshAll() {
    reload();
    reloadUnplaced();
    reloadSessions();
  }

  async function attemptMove(sessionId: number, dayIndex: number, periodIndex: number) {
    setBanner(null);
    try {
      const check = await versionsApi.checkMove(versionId, sessionId, {
        day_index: dayIndex,
        period_index: periodIndex,
        confirm: false,
      });
      if (!check.ok) {
        const messages = check.conflicts
          .map((c) => (typeof c === "object" && c && "message" in c ? String((c as { message: unknown }).message) : JSON.stringify(c)))
          .join("; ");
        setBanner({ tone: "error", text: `Move blocked: ${messages || "would break a hard constraint"}` });
        return;
      }
      await versionsApi.move(versionId, sessionId, { day_index: dayIndex, period_index: periodIndex, confirm: false });
      setBanner({ tone: "success", text: "Session moved." });
      refreshAll();
    } catch (err) {
      const detail = extractDetailObject(err);
      if (detail && Array.isArray(detail.conflicts)) {
        const messages = (detail.conflicts as unknown[])
          .map((c) => (typeof c === "object" && c && "message" in c ? String((c as { message: unknown }).message) : JSON.stringify(c)))
          .join("; ");
        setBanner({ tone: "error", text: `Move blocked: ${messages}` });
      } else {
        setBanner({ tone: "error", text: getErrorMessage(err) });
      }
    }
  }

  async function handleToggleLock(session: TimetableSessionOut) {
    setActionBusy(true);
    try {
      if (session.is_locked) await versionsApi.unlock(versionId, session.id);
      else await versionsApi.lock(versionId, session.id);
      refreshAll();
      setSelected((prev) => (prev && prev.id === session.id ? { ...prev, is_locked: !prev.is_locked } : prev));
    } catch (err) {
      setBanner({ tone: "error", text: getErrorMessage(err) });
    } finally {
      setActionBusy(false);
    }
  }

  async function handleSuggest(session: TimetableSessionOut) {
    setSuggestLoading(true);
    setSuggestions(null);
    try {
      const result = await versionsApi.suggestions(versionId, session.id);
      setSuggestions(result);
    } catch (err) {
      setBanner({ tone: "error", text: getErrorMessage(err) });
    } finally {
      setSuggestLoading(false);
    }
  }

  async function handlePublish() {
    setActionBusy(true);
    setPublishConflict(null);
    try {
      await versionsApi.publish(versionId);
      reload();
    } catch (err) {
      const detail = extractDetailObject(err);
      if (detail && Array.isArray(detail.violations)) {
        setPublishConflict({ message: String(detail.message ?? "Cannot publish"), violations: detail.violations as string[] });
      } else {
        setBanner({ tone: "error", text: getErrorMessage(err) });
      }
    } finally {
      setActionBusy(false);
    }
  }

  async function handleRollback() {
    setActionBusy(true);
    try {
      await versionsApi.rollback(versionId);
      reload();
    } catch (err) {
      setBanner({ tone: "error", text: getErrorMessage(err) });
    } finally {
      setActionBusy(false);
    }
  }

  async function handleVerify() {
    setActionBusy(true);
    try {
      await versionsApi.verify(versionId);
      reload();
      setBanner({ tone: "success", text: "Re-verified. Scores and violation counts refreshed." });
    } catch (err) {
      setBanner({ tone: "error", text: getErrorMessage(err) });
    } finally {
      setActionBusy(false);
    }
  }

  const compareFetcher = useCallback(() => {
    if (!compareToId) return Promise.resolve(null);
    return versionsApi.diff(versionId, Number(compareToId));
  }, [versionId, compareToId]);
  const { data: diff, loading: diffLoading, error: diffError } = useFetch(compareFetcher, [compareFetcher]);

  const { data: allVersions } = useFetch(versionsApi.list, []);
  const compareOptions = useMemo(
    () => (allVersions ?? []).filter((v) => v.id !== versionId).map((v) => ({ value: v.id, label: `#${v.id} — ${v.name}` })),
    [allVersions, versionId],
  );

  if (loading) return <LoadingState />;
  if (error || !version) return <ErrorState message={error ?? "Version not found"} />;

  const scorecardEntries = Object.entries(version.scorecard ?? {}).filter(
    ([, v]) => typeof v === "number" || typeof v === "string",
  );

  return (
    <div>
      <PageHeader
        title={`#${version.id} — ${version.name}`}
        description={version.notes ?? undefined}
        action={
          <div className="flex gap-2">
            <Link to="/versions">
              <Button variant="secondary">Back to versions</Button>
            </Link>
            <Link to={`/solve?version=${version.id}`}>
              <Button variant="secondary">Re-solve from here</Button>
            </Link>
          </div>
        }
      />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <Badge tone={statusTone(version.status)}>{version.status}</Badge>
        <span className="text-sm text-slate-600 dark:text-slate-300">
          Hard violations:{" "}
          <span className={version.hard_violations > 0 ? "font-semibold text-rose-600 dark:text-rose-400" : ""}>
            {version.hard_violations}
          </span>
        </span>
        <span className="text-sm text-slate-600 dark:text-slate-300">Soft score: {version.soft_score.toFixed(1)}</span>
        {version.solve_status && <Badge tone="indigo">{version.solve_status}</Badge>}
        {canWrite && (
          <div className="ml-auto flex gap-2">
            <Button size="sm" variant="secondary" disabled={actionBusy} onClick={handleVerify}>
              Re-verify
            </Button>
            {version.status === "draft" && (
              <Button
                size="sm"
                variant="primary"
                disabled={actionBusy || version.hard_violations > 0}
                title={version.hard_violations > 0 ? "Resolve all hard violations before publishing" : undefined}
                onClick={handlePublish}
              >
                Publish
              </Button>
            )}
            {version.status === "published" && (
              <Button size="sm" variant="secondary" disabled={actionBusy} onClick={handleRollback}>
                Rollback to draft
              </Button>
            )}
          </div>
        )}
      </div>

      {publishConflict && (
        <div className="mb-4 rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300">
          <p className="font-medium">{publishConflict.message}</p>
          <ul className="mt-1.5 list-inside list-disc space-y-0.5">
            {publishConflict.violations.map((v, i) => (
              <li key={i}>{v}</li>
            ))}
          </ul>
        </div>
      )}

      {unplaced && unplaced.length > 0 && (
        <div className="mb-4 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
          <div className="flex items-center justify-between gap-3">
            <p className="font-medium">
              {unplaced.length} requirement{unplaced.length === 1 ? "" : "s"} could not be placed by the solver.
            </p>
            <button type="button" className="text-xs font-semibold underline" onClick={() => setShowUnplaced((v) => !v)}>
              {showUnplaced ? "Hide details" : "Show details"}
            </button>
          </div>
          {showUnplaced && (
            <ul className="mt-2 list-inside list-disc space-y-0.5">
              {unplaced.map((u) => (
                <li key={u.id}>
                  {u.description} — {u.sessions_missing} session{u.sessions_missing === 1 ? "" : "s"} missing
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {scorecardEntries.length > 0 && (
        <Card className="mb-5 px-4 py-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Scorecard
          </p>
          <div className="flex flex-wrap gap-4">
            {scorecardEntries.map(([k, v]) => (
              <div key={k} className="text-sm">
                <span className="text-slate-500 dark:text-slate-400">{k.replace(/_/g, " ")}: </span>
                <span className="font-medium text-slate-800 dark:text-slate-100">{String(v)}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {banner && (
        <div
          className={`mb-4 rounded-md border px-4 py-2.5 text-sm ${
            banner.tone === "error"
              ? "border-rose-200 bg-rose-50 text-rose-700 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-300"
              : "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300"
          }`}
        >
          {banner.text}
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="flex gap-1 rounded-md border border-slate-200 p-1 dark:border-slate-700">
          {(["section", "teacher", "room"] as ViewAxis[]).map((a) => (
            <button
              key={a}
              type="button"
              onClick={() => setAxis(a)}
              className={`rounded px-3 py-1.5 text-sm font-medium capitalize transition ${
                axis === a
                  ? "bg-indigo-600 text-white"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              }`}
            >
              {a}
            </button>
          ))}
        </div>
        <SelectField
          label={`View by ${axis}`}
          options={entityOptions}
          value={entityId ?? ""}
          onChange={(e) => setEntityId(e.target.value ? Number(e.target.value) : null)}
          containerClassName="w-64"
        />
      </div>

      {sessionsLoading && <LoadingState />}
      {sessionsError && <ErrorState message={sessionsError} />}
      {!sessionsLoading && !sessionsError && entityId === null && (
        <EmptyState title="Nothing to show" description={`No ${axis}s exist yet in master data.`} />
      )}
      {!sessionsLoading && !sessionsError && entityId !== null && sessions && sessions.length === 0 && (
        <EmptyState title="No sessions scheduled" description="This entity has no sessions in this version yet." />
      )}
      {!sessionsLoading && !sessionsError && entityId !== null && sessions && sessions.length > 0 && days.length > 0 && (
        <TimetableGrid
          sessions={sessions}
          days={days}
          periods={periods}
          axis={axis}
          sectionLabel={sectionLabel}
          canEdit={canWrite}
          selectedSessionId={selected?.id ?? null}
          onSelect={(s) => {
            setSelected(s);
            setSuggestions(null);
          }}
          onDropSession={attemptMove}
        />
      )}

      {selected && (
        <Card className="mt-5 px-4 py-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                {selected.subject_code ?? `Session #${selected.id}`}{" "}
                {selected.is_locked && <Badge tone="amber">locked</Badge>}
              </p>
              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                {DAY_NAMES[selected.day_index] ?? `Day ${selected.day_index}`} · period {selected.period_index + 1}
                {selected.num_periods > 1 ? `–${selected.period_index + selected.num_periods}` : ""} ·{" "}
                {selected.teacher_name ?? "no teacher"} · {selected.room_code ?? "no room"}
                {selected.section_ids.length > 0 && ` · ${selected.section_ids.map(sectionLabel).join(", ")}`}
              </p>
            </div>
            {canWrite && (
              <div className="flex shrink-0 gap-2">
                <Button size="sm" variant="secondary" disabled={suggestLoading} onClick={() => handleSuggest(selected)}>
                  {suggestLoading ? "Finding…" : "Suggest slots"}
                </Button>
                <Button size="sm" variant="secondary" disabled={actionBusy} onClick={() => handleToggleLock(selected)}>
                  {selected.is_locked ? "Unlock" : "Lock"}
                </Button>
              </div>
            )}
          </div>

          {suggestions && (
            <div className="mt-3 border-t border-slate-200 pt-3 dark:border-slate-700">
              {suggestions.length === 0 ? (
                <p className="text-sm text-slate-500 dark:text-slate-400">No alternative slots found.</p>
              ) : (
                <ul className="flex flex-wrap gap-2">
                  {suggestions.map((s, i) => {
                    const d = typeof s.day_index === "number" ? s.day_index : undefined;
                    const p = typeof s.period_index === "number" ? s.period_index : undefined;
                    return (
                      <li key={i}>
                        {d !== undefined && p !== undefined ? (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => attemptMove(selected.id, d, p)}
                          >
                            {DAY_NAMES[d] ?? `Day ${d}`} · P{p + 1}
                          </Button>
                        ) : (
                          <span className="rounded bg-slate-100 px-2 py-1 text-xs dark:bg-slate-800">
                            {JSON.stringify(s)}
                          </span>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          )}
        </Card>
      )}

      {isViewer && (
        <p className="mt-3 text-xs text-slate-400 dark:text-slate-500">
          You have read-only access — moving, locking and publishing are disabled.
        </p>
      )}

      <Card className="mt-6 px-4 py-4">
        <p className="mb-3 text-sm font-semibold text-slate-800 dark:text-slate-100">Compare to another version</p>
        <SelectField
          label="Compare against"
          options={compareOptions}
          placeholder="Select a version"
          value={compareToId}
          onChange={(e) => setCompareToId(e.target.value)}
          containerClassName="max-w-sm"
        />
        {diffLoading && <LoadingState />}
        {diffError && <ErrorState message={diffError} />}
        {diff && (
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <DiffColumn title={`Moved (${diff.moved.length})`} tone="amber">
              {diff.moved.map((entry, i) => (
                <DiffRow key={i} entry={entry} />
              ))}
            </DiffColumn>
            <DiffColumn title={`Added (${diff.added.length})`} tone="green">
              {diff.added.map((entry, i) => (
                <DiffRow key={i} entry={entry} />
              ))}
            </DiffColumn>
            <DiffColumn title={`Removed (${diff.removed.length})`} tone="rose">
              {diff.removed.map((entry, i) => (
                <DiffRow key={i} entry={entry} />
              ))}
            </DiffColumn>
          </div>
        )}
        {diff && <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">{diff.unchanged} session(s) unchanged.</p>}
      </Card>

      <div className="mt-6">
        <Button variant="ghost" size="sm" onClick={() => navigate(`/diagnostics?version=${version.id}`)}>
          Run full diagnostics for this version →
        </Button>
      </div>
    </div>
  );
}

function DiffColumn({ title, tone, children }: { title: string; tone: "amber" | "green" | "rose"; children: ReactNode }) {
  const toneClass =
    tone === "amber"
      ? "border-amber-200 dark:border-amber-800"
      : tone === "green"
        ? "border-emerald-200 dark:border-emerald-800"
        : "border-rose-200 dark:border-rose-800";
  return (
    <div className={`rounded-md border p-3 ${toneClass}`}>
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">{title}</p>
      <ul className="thin-scrollbar max-h-48 space-y-1 overflow-y-auto text-xs text-slate-600 dark:text-slate-300">
        {children}
      </ul>
    </div>
  );
}

function DiffRow({ entry }: { entry: VersionDiffEntryOut }) {
  return (
    <li className="rounded bg-slate-50 px-2 py-1 dark:bg-slate-800/60">
      {entry.from || entry.to ? (
        <span>
          {formatTuple(entry.from)} → {formatTuple(entry.to)}
        </span>
      ) : (
        <span>{formatTuple(entry.now ?? entry.was)}</span>
      )}
    </li>
  );
}
