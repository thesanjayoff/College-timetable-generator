"""In-memory solve job registry. Single-process, single-college app -- this is enough
for a local deployment and keeps the API responsive while CP-SAT runs in a thread."""
import threading
import time
import uuid
from dataclasses import dataclass, field

from app.database import SessionLocal
from app.solver.builder import build_solver_input
from app.solver.service import ProgressInfo, SolveConfig, solve
from app.services.persist import persist_solve_result


@dataclass
class JobState:
    job_id: str
    version_id: int
    status: str = "running"  # running | feasible | optimal | infeasible | stopped | failed
    elapsed_seconds: float = 0.0
    objective_value: float | None = None
    best_bound: float | None = None
    solutions_found: int = 0
    unplaced_count: int = 0
    error: str | None = None
    stop_event: threading.Event = field(default_factory=threading.Event)
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None


_JOBS: dict[str, JobState] = {}
_LOCK = threading.Lock()


def get_job(job_id: str) -> JobState | None:
    with _LOCK:
        return _JOBS.get(job_id)


def request_stop(job_id: str) -> bool:
    job = get_job(job_id)
    if job is None:
        return False
    job.stop_event.set()
    return True


def start_solve_job(
    version_id: int,
    weights: dict[str, float],
    config: SolveConfig,
    locked_from_version_id: int | None,
    previous_from_version_id: int | None,
) -> str:
    job_id = uuid.uuid4().hex[:12]
    job = JobState(job_id=job_id, version_id=version_id)
    with _LOCK:
        _JOBS[job_id] = job

    def on_progress(info: ProgressInfo):
        job.elapsed_seconds = info.elapsed_seconds
        job.objective_value = info.objective_value
        job.best_bound = info.best_bound
        job.solutions_found = info.solutions_found

    def run():
        db = SessionLocal()
        try:
            data = build_solver_input(db, locked_from_version_id, previous_from_version_id)
            result = solve(data, weights, config, on_progress=on_progress, stop_event=job.stop_event)
            if not result.is_feasible:
                job.status = "infeasible"
                job.error = f"Solver status: {result.status}"
                return
            persist_solve_result(db, version_id, result)
            job.unplaced_count = len(result.unplaced)
            job.objective_value = result.objective_value
            job.best_bound = result.best_bound
            job.status = "stopped" if job.stop_event.is_set() else ("optimal" if result.status == "OPTIMAL" else "feasible")
        except Exception as exc:  # noqa: BLE001
            job.status = "failed"
            job.error = str(exc)
        finally:
            job.finished_at = time.time()
            db.close()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return job_id
