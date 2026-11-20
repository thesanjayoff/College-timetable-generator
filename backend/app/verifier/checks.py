"""Independent hard-constraint checks. Re-derives every rule from raw session rows --
does not call into app.solver at all."""
from collections import defaultdict
from dataclasses import dataclass, field

from app.verifier.types import VSession, VerifierInput

# Independently duplicated from the domain rulebook (not imported from the solver) so
# this module has zero code-sharing with app.solver.builder.
_ROOM_TYPE_FOR_SUBJECT_TYPE = {
    "theory": "classroom", "tutorial": "classroom", "project": "classroom",
    "library": "seminar_hall", "sports": "classroom", "mentoring": "classroom",
    "open_elective": "classroom", "professional_elective": "classroom", "lab": "lab",
}


@dataclass
class Violation:
    category: str
    message: str
    details: dict = field(default_factory=dict)


def _overlaps(a: VSession, b: VSession) -> bool:
    if a.day_index != b.day_index:
        return False
    return bool(set(a.periods()) & set(b.periods()))


def check_all(data: VerifierInput) -> list[Violation]:
    v: list[Violation] = []
    v += _check_exclusive_resource(data, "teacher_id", "teacher_double_booking", "Teacher")
    v += _check_exclusive_resource(data, "room_id", "room_double_booking", "Room")
    v += _check_exclusive_resource(data, "lab_batch_id", "lab_batch_double_booking", "Lab batch")
    v += _check_section_conflicts(data)
    v += _check_session_counts(data)
    v += _check_combined_elective_counts(data)
    v += _check_room_type_and_capacity(data)
    v += _check_periods_are_teaching(data)
    v += _check_teacher_room_availability(data)
    v += _check_teacher_load_limits(data)
    v += _check_section_load_limits(data)
    v += _check_elective_sync(data)
    return v


def _check_exclusive_resource(data: VerifierInput, attr: str, category: str, label: str) -> list[Violation]:
    out = []
    groups: dict[int, list[VSession]] = defaultdict(list)
    for s in data.sessions:
        val = getattr(s, attr)
        if val is not None:
            groups[val].append(s)
    for rid, sessions in groups.items():
        for i in range(len(sessions)):
            for j in range(i + 1, len(sessions)):
                a, b = sessions[i], sessions[j]
                if _overlaps(a, b):
                    out.append(Violation(
                        category=category,
                        message=f"{label} {rid} is double-booked on day {a.day_index} "
                                 f"period {a.period_index} (sessions {a.id} and {b.id})",
                        details={"resource_id": rid, "session_ids": [a.id, b.id],
                                 "day_index": a.day_index, "period_index": a.period_index},
                    ))
    return out


def _check_section_conflicts(data: VerifierInput) -> list[Violation]:
    out = []
    by_section: dict[int, list[VSession]] = defaultdict(list)
    for s in data.sessions:
        for sec in s.section_ids:
            by_section[sec].append(s)
    for sec, sessions in by_section.items():
        for i in range(len(sessions)):
            for j in range(i + 1, len(sessions)):
                a, b = sessions[i], sessions[j]
                if not _overlaps(a, b):
                    continue
                if a.sync_group is not None and a.sync_group == b.sync_group:
                    continue  # intentionally simultaneous (lab batches / elective options)
                out.append(Violation(
                    category="section_double_booking",
                    message=f"Section {sec} is double-booked on day {a.day_index} "
                             f"period {a.period_index} (sessions {a.id} and {b.id})",
                    details={"section_id": sec, "session_ids": [a.id, b.id],
                             "day_index": a.day_index, "period_index": a.period_index},
                ))
    return out


def _check_session_counts(data: VerifierInput) -> list[Violation]:
    out = []
    for req in data.requirements:
        matching = [
            s for s in data.sessions
            if s.subject_id == req.subject_id and req.section_id in s.section_ids
            and s.elective_basket_id is None and s.combined_class_id is None
        ]
        occurrences = {(s.day_index, s.period_index) for s in matching}
        if len(occurrences) != req.sessions_per_week:
            out.append(Violation(
                category="session_count_mismatch",
                message=f"Subject {req.subject_id} / Section {req.section_id}: expected "
                         f"{req.sessions_per_week} sessions/week, found {len(occurrences)}",
                details={"subject_id": req.subject_id, "section_id": req.section_id,
                         "expected": req.sessions_per_week, "found": len(occurrences)},
            ))
        for s in matching:
            if s.num_periods != req.block_size:
                out.append(Violation(
                    category="block_size_mismatch",
                    message=f"Session {s.id} for subject {req.subject_id}/section {req.section_id} "
                             f"has {s.num_periods} periods, expected block size {req.block_size}",
                    details={"session_id": s.id, "expected": req.block_size, "found": s.num_periods},
                ))
    return out


def _check_combined_elective_counts(data: VerifierInput) -> list[Violation]:
    out = []
    for cc_id, expected in data.expected_combined.items():
        matching = [s for s in data.sessions if s.combined_class_id == cc_id]
        occurrences = {(s.day_index, s.period_index) for s in matching}
        if len(occurrences) != expected["sessions_per_week"]:
            out.append(Violation(
                category="combined_count_mismatch",
                message=f"Combined class {cc_id}: expected {expected['sessions_per_week']} "
                         f"sessions/week, found {len(occurrences)}",
                details={"combined_class_id": cc_id},
            ))
        for s in matching:
            if set(s.section_ids) != set(expected["section_ids"]):
                out.append(Violation(
                    category="combined_sections_mismatch",
                    message=f"Combined class session {s.id} covers sections {s.section_ids}, "
                             f"expected {expected['section_ids']}",
                    details={"session_id": s.id},
                ))

    for basket_id, expected in data.expected_elective.items():
        matching = [s for s in data.sessions if s.elective_basket_id == basket_id]
        by_slot: dict[tuple[int, int], list[VSession]] = defaultdict(list)
        for s in matching:
            by_slot[(s.day_index, s.period_index)].append(s)
        if len(by_slot) != expected["sessions_per_week"]:
            out.append(Violation(
                category="elective_count_mismatch",
                message=f"Elective basket {basket_id}: expected {expected['sessions_per_week']} "
                         f"sessions/week, found {len(by_slot)}",
                details={"basket_id": basket_id},
            ))
        expected_option_ids = {o["id"] for o in expected["options"]}
        for slot, sessions_here in by_slot.items():
            found_subjects = {s.subject_id for s in sessions_here}
            expected_subjects = {o["subject_id"] for o in expected["options"]}
            if found_subjects != expected_subjects:
                out.append(Violation(
                    category="elective_options_incomplete",
                    message=f"Elective basket {basket_id} occurrence at day {slot[0]} period {slot[1]} "
                             f"has options for subjects {found_subjects}, expected {expected_subjects}",
                    details={"basket_id": basket_id, "slot": slot},
                ))
    return out


def _check_room_type_and_capacity(data: VerifierInput) -> list[Violation]:
    out = []
    req_by_key = {(r.subject_id, r.section_id): r for r in data.requirements}
    elective_option_by_subject: dict[int, dict] = {}
    for basket in data.expected_elective.values():
        for opt in basket["options"]:
            elective_option_by_subject[opt["subject_id"]] = opt

    for s in data.sessions:
        room = data.rooms.get(s.room_id) if s.room_id else None
        if room is None:
            continue
        required_type, required_capacity = None, None
        if s.combined_class_id and s.combined_class_id in data.expected_combined:
            exp = data.expected_combined[s.combined_class_id]
            required_type, required_capacity = exp["room_type"], exp["capacity"]
        elif s.elective_basket_id and s.subject_id in elective_option_by_subject:
            opt = elective_option_by_subject[s.subject_id]
            required_type, required_capacity = opt["room_type"], opt["capacity"]
        else:
            for sec in s.section_ids:
                req = req_by_key.get((s.subject_id, sec))
                if req:
                    required_type = _ROOM_TYPE_FOR_SUBJECT_TYPE.get(req.subject_type, "classroom")
                    required_capacity = (
                        data.lab_batch_strength.get(s.lab_batch_id, 0) if s.lab_batch_id
                        else data.sections[sec].strength if sec in data.sections else 0
                    )
        if required_type and room.room_type != required_type:
            out.append(Violation(
                category="room_type_mismatch",
                message=f"Session {s.id} needs a {required_type} room but was given room {room.id} "
                         f"({room.room_type})",
                details={"session_id": s.id, "required": required_type, "found": room.room_type},
            ))
        if required_capacity and room.capacity < required_capacity:
            out.append(Violation(
                category="room_capacity_exceeded",
                message=f"Session {s.id} needs capacity {required_capacity} but room {room.id} "
                         f"only holds {room.capacity}",
                details={"session_id": s.id, "required": required_capacity, "capacity": room.capacity},
            ))
    return out


def _check_periods_are_teaching(data: VerifierInput) -> list[Violation]:
    out = []
    for s in data.sessions:
        for sec in s.section_ids:
            info = data.sections.get(sec)
            if info is None:
                continue
            structure = data.structures.get(info.structure_id)
            if structure is None:
                continue
            teaching = set(structure.teaching_periods_for_day(s.day_index))
            bad = [p for p in s.periods() if p not in teaching]
            if bad:
                out.append(Violation(
                    category="non_teaching_period_used",
                    message=f"Session {s.id} uses non-teaching period(s) {bad} on day {s.day_index} "
                             f"for section {sec}",
                    details={"session_id": s.id, "section_id": sec, "periods": bad},
                ))
            break  # one representative section is enough; all share the same structure in practice
    return out


def _check_teacher_room_availability(data: VerifierInput) -> list[Violation]:
    out = []
    for s in data.sessions:
        if s.teacher_id is not None:
            t = data.teachers.get(s.teacher_id)
            if t:
                if s.day_index in t.day_off:
                    out.append(Violation(
                        category="teacher_unavailable",
                        message=f"Session {s.id} assigns teacher {s.teacher_id} on their day off "
                                 f"(day {s.day_index})",
                        details={"session_id": s.id, "teacher_id": s.teacher_id},
                    ))
                for p in s.periods():
                    if (s.day_index, p) in t.unavailable_slots:
                        out.append(Violation(
                            category="teacher_unavailable",
                            message=f"Session {s.id} assigns teacher {s.teacher_id} during an unavailable "
                                     f"slot (day {s.day_index}, period {p})",
                            details={"session_id": s.id, "teacher_id": s.teacher_id, "period_index": p},
                        ))
        if s.room_id is not None:
            r = data.rooms.get(s.room_id)
            if r:
                for p in s.periods():
                    if (s.day_index, p) in r.unavailable_slots:
                        out.append(Violation(
                            category="room_unavailable",
                            message=f"Session {s.id} uses room {s.room_id} during an unavailable "
                                     f"slot (day {s.day_index}, period {p})",
                            details={"session_id": s.id, "room_id": s.room_id, "period_index": p},
                        ))
    return out


def _check_teacher_load_limits(data: VerifierInput) -> list[Violation]:
    out = []
    by_teacher: dict[int, list[VSession]] = defaultdict(list)
    for s in data.sessions:
        if s.teacher_id is not None:
            by_teacher[s.teacher_id].append(s)
    for tid, sessions in by_teacher.items():
        info = data.teachers.get(tid)
        if info is None:
            continue
        occupied: set[tuple[int, int]] = set()
        for s in sessions:
            for p in s.periods():
                occupied.add((s.day_index, p))
        by_day: dict[int, set[int]] = defaultdict(set)
        for d, p in occupied:
            by_day[d].add(p)

        week_total = len(occupied)
        if info.max_periods_per_week is not None and week_total > info.max_periods_per_week:
            out.append(Violation(
                category="teacher_overload_week",
                message=f"Teacher {tid} is scheduled for {week_total} periods/week, "
                         f"exceeding the limit of {info.max_periods_per_week}",
                details={"teacher_id": tid, "found": week_total, "limit": info.max_periods_per_week},
            ))
        for d, periods in by_day.items():
            if info.max_periods_per_day is not None and len(periods) > info.max_periods_per_day:
                out.append(Violation(
                    category="teacher_overload_day",
                    message=f"Teacher {tid} is scheduled for {len(periods)} periods on day {d}, "
                             f"exceeding the limit of {info.max_periods_per_day}",
                    details={"teacher_id": tid, "day_index": d, "found": len(periods),
                             "limit": info.max_periods_per_day},
                ))
            if info.max_consecutive_periods is not None:
                run = 0
                for p in sorted(periods):
                    prev_in_run = (p - 1) in periods
                    run = run + 1 if prev_in_run else 1
                    if run > info.max_consecutive_periods:
                        out.append(Violation(
                            category="teacher_too_many_consecutive",
                            message=f"Teacher {tid} has more than {info.max_consecutive_periods} "
                                     f"consecutive periods on day {d}",
                            details={"teacher_id": tid, "day_index": d},
                        ))
                        break
    return out


def _check_section_load_limits(data: VerifierInput) -> list[Violation]:
    out = []
    by_section: dict[int, set[tuple[int, int]]] = defaultdict(set)
    for s in data.sessions:
        for sec in s.section_ids:
            for p in s.periods():
                by_section[sec].add((s.day_index, p))
    for sec, occupied in by_section.items():
        info = data.sections.get(sec)
        if info is None:
            continue
        by_day: dict[int, set[int]] = defaultdict(set)
        for d, p in occupied:
            by_day[d].add(p)
        for d, periods in by_day.items():
            if info.max_periods_per_day is not None and len(periods) > info.max_periods_per_day:
                out.append(Violation(
                    category="section_overload_day",
                    message=f"Section {sec} has {len(periods)} periods on day {d}, "
                             f"exceeding the limit of {info.max_periods_per_day}",
                    details={"section_id": sec, "day_index": d},
                ))
            if info.max_consecutive_periods is not None:
                run = 0
                for p in sorted(periods):
                    prev_in_run = (p - 1) in periods
                    run = run + 1 if prev_in_run else 1
                    if run > info.max_consecutive_periods:
                        out.append(Violation(
                            category="section_too_many_consecutive",
                            message=f"Section {sec} has more than {info.max_consecutive_periods} "
                                     f"consecutive periods on day {d}",
                            details={"section_id": sec, "day_index": d},
                        ))
                        break
    return out


def _check_elective_sync(data: VerifierInput) -> list[Violation]:
    out = []
    by_basket: dict[int, list[VSession]] = defaultdict(list)
    for s in data.sessions:
        if s.elective_basket_id is not None:
            by_basket[s.elective_basket_id].append(s)
    for basket_id, sessions in by_basket.items():
        by_group: dict[str | None, list[VSession]] = defaultdict(list)
        for s in sessions:
            by_group[s.sync_group].append(s)
        for group_key, members in by_group.items():
            slots = {(m.day_index, m.period_index) for m in members}
            if len(slots) > 1:
                out.append(Violation(
                    category="elective_not_synchronized",
                    message=f"Elective basket {basket_id} options in sync group {group_key} are not "
                             f"scheduled at the same slot: {sorted(slots)}",
                    details={"basket_id": basket_id, "slots": sorted(slots)},
                ))
    return out
