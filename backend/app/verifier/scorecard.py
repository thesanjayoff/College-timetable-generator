"""Recomputes every soft-constraint penalty from scratch in plain Python, independent of
the solver's CP-SAT objective (app.solver.soft). Produces the admin-facing scorecard."""
from collections import defaultdict

from app.verifier.types import VSession, VerifierInput


def _occupied_periods(sessions: list[VSession]) -> set[tuple[int, int]]:
    out = set()
    for s in sessions:
        for p in s.periods():
            out.add((s.day_index, p))
    return out


def _gaps_for_day(occupied_periods: set[int], all_periods: list[int]) -> int:
    if len(all_periods) < 3:
        return 0
    periods = sorted(all_periods)
    occ = [p in occupied_periods for p in periods]
    first = next((i for i, o in enumerate(occ) if o), None)
    last = next((i for i in range(len(occ) - 1, -1, -1) if occ[i]), None)
    if first is None or last is None or first >= last:
        return 0
    return sum(1 for i in range(first + 1, last) if not occ[i])


def compute_scorecard(data: VerifierInput, weights: dict[str, float]) -> dict:
    by_section: dict[int, list[VSession]] = defaultdict(list)
    by_teacher: dict[int, list[VSession]] = defaultdict(list)
    for s in data.sessions:
        for sec in s.section_ids:
            by_section[sec].append(s)
        if s.teacher_id is not None:
            by_teacher[s.teacher_id].append(s)

    raw: dict[str, float] = defaultdict(float)

    # --- gaps ---
    for sec, sessions in by_section.items():
        info = data.sections.get(sec)
        if info is None:
            continue
        structure = data.structures.get(info.structure_id)
        if structure is None:
            continue
        occ = _occupied_periods(sessions)
        by_day = defaultdict(set)
        for d, p in occ:
            by_day[d].add(p)
        for d in {s.day_index for s in sessions} | set(by_day.keys()):
            periods = structure.teaching_periods_for_day(d)
            raw["section_gaps"] += _gaps_for_day(by_day.get(d, set()), periods)

    for t, sessions in by_teacher.items():
        structures_used = {data.sections[sec].structure_id for s in sessions for sec in s.section_ids
                            if sec in data.sections}
        structure = data.structures.get(next(iter(structures_used), None))
        occ = _occupied_periods(sessions)
        by_day = defaultdict(set)
        for d, p in occ:
            by_day[d].add(p)
        if structure is None:
            continue
        for d in by_day:
            periods = structure.teaching_periods_for_day(d)
            raw["teacher_gaps"] += _gaps_for_day(by_day[d], periods)

    # --- same subject twice a day ---
    for sec, sessions in by_section.items():
        per_day_subject: dict[tuple[int, int], set[tuple[int, int]]] = defaultdict(set)
        for s in sessions:
            if s.subject_id is None:
                continue
            per_day_subject[(s.day_index, s.subject_id)].add((s.day_index, s.period_index))
        for (_, _), occurrences in per_day_subject.items():
            if len(occurrences) > 1:
                raw["same_subject_twice_a_day"] += len(occurrences) - 1

    # --- section daily balance ---
    for sec, sessions in by_section.items():
        occ = _occupied_periods(sessions)
        by_day = defaultdict(set)
        for d, p in occ:
            by_day[d].add(p)
        totals = list(len(v) for v in by_day.values())
        if not totals:
            continue
        avg = sum(totals) / len(totals)
        raw["section_daily_balance"] += sum(abs(t - avg) for t in totals)

    # --- teacher workload balance ---
    weekly_totals = []
    for t, sessions in by_teacher.items():
        weekly_totals.append(len(_occupied_periods(sessions)))
    if len(weekly_totals) > 1:
        avg = sum(weekly_totals) / len(weekly_totals)
        raw["teacher_workload_balance"] = sum(abs(x - avg) for x in weekly_totals)

    # --- teacher preferences ---
    for t, info in data.teachers.items():
        sessions = by_teacher.get(t, [])
        if not sessions:
            continue
        occ = _occupied_periods(sessions)
        by_day = defaultdict(set)
        for d, p in occ:
            by_day[d].add(p)
        structures_used = {data.sections[sec].structure_id for s in sessions for sec in s.section_ids
                            if sec in data.sections}
        structure = data.structures.get(next(iter(structures_used), None))
        for pref in info.preferences:
            ptype = pref["type"]
            w = pref.get("weight", 1.0)
            if ptype == "free_day":
                raw["teacher_free_day"] += len(by_day.get(pref["day_index"], set())) * w
            elif ptype == "preferred_day":
                for d, periods in by_day.items():
                    if d != pref["day_index"]:
                        raw["teacher_preferred_day"] += len(periods) * w
            elif ptype == "no_first_period" and structure:
                for d, periods in by_day.items():
                    fp = structure.first_teaching_period(d)
                    if fp is not None and fp in periods:
                        raw["teacher_no_first_period"] += w
            elif ptype == "no_last_period" and structure:
                for d, periods in by_day.items():
                    lp = structure.last_teaching_period(d)
                    if lp is not None and lp in periods:
                        raw["teacher_no_last_period"] += w
            elif ptype == "avoid_back_to_back":
                for d, periods in by_day.items():
                    sp = sorted(periods)
                    for i in range(len(sp) - 1):
                        if sp[i + 1] == sp[i] + 1:
                            raw["teacher_avoid_back_to_back"] += w

    # --- lab afternoon preference & heavy-subject-last-period ---
    req_by_key = {(r.subject_id, r.section_id): r for r in data.requirements}
    for s in data.sessions:
        for sec in s.section_ids:
            req = req_by_key.get((s.subject_id, sec))
            if req is None:
                continue
            info = data.sections.get(sec)
            structure = data.structures.get(info.structure_id) if info else None
            if req.prefer_afternoon and structure is not None:
                periods = structure.teaching_periods_for_day(s.day_index)
                if periods:
                    cutoff = periods[len(periods) // 2]
                    if s.period_index < cutoff:
                        raw["lab_afternoon_preference"] += 1
            if req.avoid_last_period and structure is not None:
                last = structure.last_teaching_period(s.day_index)
                if last is not None and s.period_index + s.num_periods - 1 >= last:
                    raw["heavy_subject_last_period"] += 1

    weighted = {k: raw.get(k, 0) * weights.get(k, 0) for k in weights if k != "stability"}
    total = sum(weighted.values())
    return {
        "raw": dict(raw),
        "weighted": weighted,
        "total_soft_score": total,
    }
