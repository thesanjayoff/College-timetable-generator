from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.timetable import TimetableVersion
from app.models.weight import DEFAULT_WEIGHTS, PRESETS
from app.solver.diagnosis import run_prechecks
from app.solver.service import SolveConfig
from app.services.solve_jobs import get_job, request_stop, start_solve_job

router = APIRouter(prefix="/api/versions/{version_id}/solve", tags=["solve"])


class SolveRequest(BaseModel):
    weight_preset: str | None = None
    weights: dict[str, float] | None = None
    time_limit_seconds: float = 60.0
    num_workers: int = 8
    random_seed: int | None = None
    deterministic: bool = False
    stability_weight: float = 0.0
    lock_from_self: bool = True
    stabilize_against_parent: bool = True


def _resolve_weights(req: SolveRequest) -> dict[str, float]:
    if req.weights:
        return {**DEFAULT_WEIGHTS, **req.weights}
    if req.weight_preset and req.weight_preset in PRESETS:
        return PRESETS[req.weight_preset]
    return DEFAULT_WEIGHTS


@router.post("")
def start_solve(version_id: int, payload: SolveRequest, db: Session = Depends(get_db)):
    v = db.get(TimetableVersion, version_id)
    if v is None:
        raise HTTPException(404, "Version not found")
    weights = _resolve_weights(payload)
    config = SolveConfig(
        time_limit_seconds=payload.time_limit_seconds, num_workers=payload.num_workers,
        random_seed=payload.random_seed, deterministic=payload.deterministic,
        stability_weight=payload.stability_weight,
    )
    locked_from = version_id if payload.lock_from_self else None
    previous_from = v.parent_version_id if payload.stabilize_against_parent else None
    job_id = start_solve_job(version_id, weights, config, locked_from, previous_from)
    v.solve_status = "running"
    db.commit()
    return {"job_id": job_id}


@router.get("/jobs/{job_id}")
def job_status(version_id: int, job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return {
        "job_id": job.job_id, "version_id": job.version_id, "status": job.status,
        "elapsed_seconds": job.elapsed_seconds, "objective_value": job.objective_value,
        "best_bound": job.best_bound, "solutions_found": job.solutions_found,
        "unplaced_count": job.unplaced_count, "error": job.error,
    }


@router.post("/jobs/{job_id}/stop")
def stop_job(version_id: int, job_id: str):
    if not request_stop(job_id):
        raise HTTPException(404, "Job not found")
    return {"ok": True}


@router.get("/prechecks")
def prechecks(version_id: int, db: Session = Depends(get_db)):
    findings = run_prechecks(db)
    return [
        {"category": f.category, "message": f.message, "severity": f.severity,
         "suggestions": f.suggestions, "details": f.details}
        for f in findings
    ]


@router.get("/presets")
def list_presets():
    return {"presets": list(PRESETS.keys()), "weights": PRESETS}
