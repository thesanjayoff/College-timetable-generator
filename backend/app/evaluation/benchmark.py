"""Scale benchmark: generates synthetic colleges of increasing size and reports time to
first feasible solution, solution quality at several checkpoints, memory use, and the
optimality gap where known. Run with:  python -m app.evaluation.benchmark [sizes...]
"""
import json
import sys
import time

import psutil
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
import app.models  # noqa
from app.models.timetable import TimetableVersion
from app.seed.generate_sample_college import generate_college
from app.solver.builder import build_solver_input
from app.solver.service import ProgressInfo, SolveConfig, solve
from app.verifier.verify import verify_version
from app.services.persist import persist_solve_result

DEFAULT_CHECKPOINTS = (60, 300, 1800)  # 1 min, 5 min, 30 min


def run_one(size: str, checkpoints=DEFAULT_CHECKPOINTS, seed: int = 42, weights=None,
            deterministic: bool = False, num_workers: int = 8) -> dict:
    weights = weights or {"section_gaps": 10, "teacher_gaps": 8, "same_subject_twice_a_day": 12,
                           "section_daily_balance": 6, "teacher_workload_balance": 8}
    engine = create_engine(f"sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    gen_t0 = time.time()
    stats = generate_college(db, size=size, seed=seed)
    gen_time = time.time() - gen_t0

    version = TimetableVersion(name=f"bench-{size}")
    db.add(version)
    db.commit()

    build_t0 = time.time()
    data = build_solver_input(db)
    build_time = time.time() - build_t0
    n_groups = len(data.groups)
    n_occurrences = sum(g.sessions_per_week for g in data.groups)

    process = psutil.Process()
    snapshots: list[dict] = []
    first_feasible_at = {"t": None}
    checkpoint_set = sorted(checkpoints)
    recorded = set()

    def on_progress(info: ProgressInfo):
        if first_feasible_at["t"] is None:
            first_feasible_at["t"] = info.elapsed_seconds
        rss_mb = process.memory_info().rss / (1024 * 1024)
        snapshots.append({"t": info.elapsed_seconds, "objective": info.objective_value,
                           "bound": info.best_bound, "rss_mb": rss_mb})
        for cp in checkpoint_set:
            if info.elapsed_seconds >= cp and cp not in recorded:
                recorded.add(cp)

    config = SolveConfig(time_limit_seconds=max(checkpoint_set), num_workers=num_workers,
                          deterministic=deterministic, random_seed=seed)
    solve_t0 = time.time()
    result = solve(data, weights, config, on_progress=on_progress)
    solve_time = time.time() - solve_t0

    def quality_at(cp: float):
        candidates = [s for s in snapshots if s["t"] <= cp]
        if not candidates:
            return None
        return candidates[-1]

    checkpoint_report = {str(cp): quality_at(cp) for cp in checkpoint_set}
    peak_rss_mb = max((s["rss_mb"] for s in snapshots), default=process.memory_info().rss / (1024 * 1024))

    gap = None
    if result.objective_value and result.best_bound is not None:
        denom = abs(result.objective_value) or 1
        gap = abs(result.objective_value - result.best_bound) / denom

    hard_violations = None
    if result.is_feasible:
        persist_solve_result(db, version.id, result)
        report = verify_version(db, version.id)
        hard_violations = len(report.hard_violations)

    return {
        "size": size, "stats": stats, "generation_time_s": round(gen_time, 3),
        "model_build_time_s": round(build_time, 3), "groups": n_groups, "occurrences": n_occurrences,
        "solve_time_s": round(solve_time, 3), "solve_status": result.status,
        "time_to_first_feasible_s": first_feasible_at["t"], "unplaced_count": len(result.unplaced),
        "final_objective": result.objective_value, "final_bound": result.best_bound,
        "optimality_gap": gap, "peak_rss_mb": round(peak_rss_mb, 1),
        "checkpoints": checkpoint_report, "hard_violations_after_verify": hard_violations,
    }


def main():
    sizes = sys.argv[1:] or ["small", "medium"]
    checkpoints = DEFAULT_CHECKPOINTS if "large" in sizes else (10, 30, 60)
    results = []
    for size in sizes:
        print(f"--- benchmarking {size} ---", file=sys.stderr)
        results.append(run_one(size, checkpoints=checkpoints))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
