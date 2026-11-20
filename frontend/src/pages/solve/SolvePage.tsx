import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useFetch } from "../../hooks/useFetch";
import { solveApi } from "../../api/resources";
import { getErrorMessage } from "../../api/client";
import { WEIGHT_CATEGORIES, SOLVE_TERMINAL_STATUSES } from "../../api/types";
import type { SolveJobOut } from "../../api/types";
import {
  Badge,
  Button,
  Card,
  CheckboxField,
  ErrorState,
  PageHeader,
  SelectField,
  TextField,
} from "../../components/ui";
import { useAuth } from "../../context/AuthContext";
import { useVersionIdParam, VersionPicker } from "../versions/VersionPicker";
import { FindingsList } from "../diagnostics/FindingsList";
import { solveStatusTone } from "../versions/versionStatus";

function defaultWeights(): Record<string, number> {
  const result: Record<string, number> = {};
  for (const cat of WEIGHT_CATEGORIES) result[cat.key] = 5;
  return result;
}

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

export default function SolvePage() {
  const { canWrite } = useAuth();
  const [versionId, setVersionId] = useVersionIdParam();

  const presetsFetcher = useCallback(() => {
    if (versionId === null) return Promise.resolve(null);
    return solveApi.presets(versionId);
  }, [versionId]);
  const { data: presetsData } = useFetch(presetsFetcher, [presetsFetcher]);

  const [preset, setPreset] = useState<string>("");
  const [customize, setCustomize] = useState(false);
  const [weights, setWeights] = useState<Record<string, number>>(defaultWeights());
  const [timeLimit, setTimeLimit] = useState("60");
  const [numWorkers, setNumWorkers] = useState("8");
  const [randomSeed, setRandomSeed] = useState("");
  const [deterministic, setDeterministic] = useState(false);
  const [stabilityWeight, setStabilityWeight] = useState("0");
  const [lockFromSelf, setLockFromSelf] = useState(true);
  const [stabilizeAgainstParent, setStabilizeAgainstParent] = useState(true);

  useEffect(() => {
    setJobId(null);
    setJob(null);
    setStartError(null);
  }, [versionId]);

  const [precheckNonce, setPrecheckNonce] = useState(0);
  const precheckFetcher = useCallback(() => {
    if (versionId === null || precheckNonce === 0) return Promise.resolve(null);
    return solveApi.prechecks(versionId);
  }, [versionId, precheckNonce]);
  const { data: findings, loading: precheckLoading, error: precheckError } = useFetch(precheckFetcher, [precheckFetcher]);
  const blockingCount = (findings ?? []).filter((f) => f.severity === "blocking").length;

  const [startError, setStartError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<SolveJobOut | null>(null);
  const [stopping, setStopping] = useState(false);
  const pollRef = useRef<number | null>(null);

  const weightGroups = useMemo(() => {
    const map = new Map<string, typeof WEIGHT_CATEGORIES>();
    for (const cat of WEIGHT_CATEGORIES) {
      const list = map.get(cat.group) ?? [];
      list.push(cat);
      map.set(cat.group, list);
    }
    return Array.from(map.entries());
  }, []);

  useEffect(() => {
    if (preset && presetsData?.weights[preset]) {
      setWeights({ ...defaultWeights(), ...presetsData.weights[preset] });
    }
  }, [preset, presetsData]);

  useEffect(() => {
    if (!jobId || !versionId) return;
    function poll() {
      solveApi
        .jobStatus(versionId!, jobId!)
        .then((j) => {
          setJob(j);
          if (SOLVE_TERMINAL_STATUSES.includes(j.status)) {
            if (pollRef.current) window.clearInterval(pollRef.current);
          }
        })
        .catch(() => {
          if (pollRef.current) window.clearInterval(pollRef.current);
        });
    }
    poll();
    pollRef.current = window.setInterval(poll, 1500);
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId, versionId]);

  async function handleStart() {
    if (versionId === null) return;
    setStarting(true);
    setStartError(null);
    try {
      const result = await solveApi.start(versionId, {
        weight_preset: customize ? null : preset || null,
        weights: customize ? weights : null,
        time_limit_seconds: Number(timeLimit) || 60,
        num_workers: Number(numWorkers) || 8,
        random_seed: randomSeed ? Number(randomSeed) : null,
        deterministic,
        stability_weight: Number(stabilityWeight) || 0,
        lock_from_self: lockFromSelf,
        stabilize_against_parent: stabilizeAgainstParent,
      });
      setJobId(result.job_id);
      setJob(null);
    } catch (err) {
      setStartError(getErrorMessage(err));
    } finally {
      setStarting(false);
    }
  }

  async function handleStop() {
    if (versionId === null || !jobId) return;
    setStopping(true);
    try {
      await solveApi.stopJob(versionId, jobId);
    } catch (err) {
      setStartError(getErrorMessage(err));
    } finally {
      setStopping(false);
    }
  }

  const isRunning = job?.status === "running";
  const gapPercent = ((): number | null => {
    if (!job || job.objective_value === null || job.best_bound === null || job.objective_value === 0) return null;
    return Math.abs(((job.objective_value - job.best_bound) / job.objective_value) * 100);
  })();

  return (
    <div>
      <PageHeader
        title="Solve"
        description="Run the CP-SAT solver against a version, monitor progress live, and stop early while keeping the best result found."
      />

      <div className="mb-5 max-w-sm">
        <VersionPicker value={versionId} onChange={setVersionId} />
      </div>

      {versionId === null && (
        <p className="text-sm text-slate-500 dark:text-slate-400">Select a version to configure and run a solve.</p>
      )}

      {versionId !== null && (
        <>
          <Card className="mb-5 px-4 py-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">Prechecks</p>
              <Button size="sm" variant="secondary" disabled={precheckLoading} onClick={() => setPrecheckNonce((n) => n + 1)}>
                {precheckLoading ? "Running…" : "Run prechecks first"}
              </Button>
            </div>
            {precheckError && <div className="mt-3"><ErrorState message={precheckError} /></div>}
            {findings && (
              <div className="mt-3">
                {blockingCount > 0 && (
                  <p className="mb-2 text-sm font-medium text-rose-600 dark:text-rose-400">
                    {blockingCount} blocking issue{blockingCount === 1 ? "" : "s"} found — the solve is likely to fail or
                    leave sessions unplaced until these are fixed.
                  </p>
                )}
                <FindingsList findings={findings} />
              </div>
            )}
          </Card>

          {canWrite ? (
            <Card className="mb-5 px-4 py-4">
              <p className="mb-3 text-sm font-semibold text-slate-800 dark:text-slate-100">Solve configuration</p>
              <div className="grid gap-3 sm:grid-cols-2">
                <SelectField
                  label="Weight preset"
                  disabled={customize}
                  placeholder="Default weights"
                  options={(presetsData?.presets ?? []).map((p) => ({ value: p, label: p }))}
                  value={preset}
                  onChange={(e) => setPreset(e.target.value)}
                />
                <div className="flex items-center">
                  <CheckboxField
                    label="Customize weights"
                    checked={customize}
                    onChange={(e) => setCustomize(e.target.checked)}
                    hint="Override individual soft-objective weights below"
                  />
                </div>
              </div>

              {customize && (
                <div className="mt-4 flex flex-col gap-5 rounded-md bg-slate-50 p-3 dark:bg-slate-800/60">
                  {weightGroups.map(([group, cats]) => (
                    <div key={group}>
                      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                        {group}
                      </p>
                      <div className="flex flex-col gap-3">
                        {cats.map((cat) => (
                          <div key={cat.key} className="flex items-center gap-3">
                            <label className="w-56 shrink-0 text-sm text-slate-700 dark:text-slate-200">{cat.label}</label>
                            <input
                              type="range"
                              min={0}
                              max={30}
                              step={0.5}
                              value={weights[cat.key] ?? 0}
                              onChange={(e) => setWeights({ ...weights, [cat.key]: Number(e.target.value) })}
                              className="flex-1 accent-indigo-600"
                            />
                            <input
                              type="number"
                              min={0}
                              max={100}
                              step={0.5}
                              value={weights[cat.key] ?? 0}
                              onChange={(e) => setWeights({ ...weights, [cat.key]: Number(e.target.value) || 0 })}
                              className="w-16 rounded-md border border-slate-300 bg-white px-2 py-1 text-right text-sm text-slate-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-4 grid gap-3 sm:grid-cols-4">
                <TextField
                  label="Time limit (seconds)"
                  type="number"
                  min={1}
                  value={timeLimit}
                  onChange={(e) => setTimeLimit(e.target.value)}
                />
                <TextField label="Workers" type="number" min={1} value={numWorkers} onChange={(e) => setNumWorkers(e.target.value)} />
                <TextField
                  label="Random seed (optional)"
                  type="number"
                  value={randomSeed}
                  onChange={(e) => setRandomSeed(e.target.value)}
                />
                <TextField
                  label="Stability weight"
                  type="number"
                  min={0}
                  value={stabilityWeight}
                  onChange={(e) => setStabilityWeight(e.target.value)}
                />
              </div>

              <div className="mt-4 flex flex-wrap gap-5">
                <CheckboxField label="Deterministic" checked={deterministic} onChange={(e) => setDeterministic(e.target.checked)} />
                <CheckboxField
                  label="Lock sessions already locked in this version"
                  checked={lockFromSelf}
                  onChange={(e) => setLockFromSelf(e.target.checked)}
                />
                <CheckboxField
                  label="Stabilize against parent version"
                  checked={stabilizeAgainstParent}
                  onChange={(e) => setStabilizeAgainstParent(e.target.checked)}
                />
              </div>

              {startError && <div className="mt-4"><ErrorState message={startError} /></div>}

              <div className="mt-4 flex gap-2">
                <Button variant="primary" disabled={starting || isRunning} onClick={handleStart}>
                  {starting ? "Starting…" : isRunning ? "Running…" : "Start solve"}
                </Button>
              </div>
            </Card>
          ) : (
            <p className="mb-5 text-sm text-slate-500 dark:text-slate-400">
              You have read-only access — starting a solve is disabled.
            </p>
          )}

          {job && (
            <Card className="px-4 py-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">Job {job.job_id}</p>
                <Badge tone={solveStatusTone(job.status)}>{job.status}</Badge>
              </div>
              <div className="mt-3 grid gap-3 text-sm sm:grid-cols-5">
                <Stat label="Elapsed" value={formatElapsed(job.elapsed_seconds)} />
                <Stat label="Objective" value={job.objective_value !== null ? job.objective_value.toFixed(2) : "—"} />
                <Stat label="Best bound" value={job.best_bound !== null ? job.best_bound.toFixed(2) : "—"} />
                <Stat label="Gap" value={gapPercent !== null ? `${gapPercent.toFixed(1)}%` : "—"} />
                <Stat label="Solutions found" value={String(job.solutions_found)} />
              </div>
              {job.error && <div className="mt-3"><ErrorState message={job.error} /></div>}

              {isRunning && canWrite && (
                <div className="mt-4">
                  <Button variant="danger" disabled={stopping} onClick={handleStop}>
                    {stopping ? "Stopping…" : "Stop (keeps best result found so far)"}
                  </Button>
                </div>
              )}

              {!isRunning && SOLVE_TERMINAL_STATUSES.includes(job.status) && (
                <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-slate-200 pt-3 dark:border-slate-700">
                  <p className="text-sm text-slate-600 dark:text-slate-300">
                    {job.unplaced_count > 0 ? (
                      <span className="font-medium text-amber-600 dark:text-amber-400">
                        {job.unplaced_count} requirement(s) remain unplaced.
                      </span>
                    ) : (
                      <span className="font-medium text-emerald-600 dark:text-emerald-400">
                        Every requirement was placed.
                      </span>
                    )}
                  </p>
                  <Link to={`/versions/${versionId}`}>
                    <Button size="sm" variant="secondary">
                      Open version →
                    </Button>
                  </Link>
                </div>
              )}
            </Card>
          )}
        </>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</p>
      <p className="font-medium text-slate-800 dark:text-slate-100">{value}</p>
    </div>
  );
}
