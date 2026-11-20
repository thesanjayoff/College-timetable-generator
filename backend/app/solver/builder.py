"""Converts the database into the solver's IR (app.solver.ir). This is the only module
that should import both the ORM and the solver IR."""
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.allocation import Allocation
from app.models.college import Section
from app.models.combined import CombinedClass, CombinedClassSection
from app.models.elective import ElectiveBasket, ElectiveOption, ElectiveParticipation
from app.models.enums import RoomType, SubjectType
from app.models.room import Room, RoomUnavailability
from app.models.structure import TimeStructure
from app.models.teacher import Teacher, TeacherPreference, TeacherSubject, TeacherUnavailability
from app.models.timetable import SessionSection, TimetableSession
from app.solver.grid import TimeGrid
from app.solver.ir import LockedSession, PreviousSession, ReqPart, RequirementGroup, SolverInput

SUBJECT_ROOM_TYPE = {
    SubjectType.THEORY: RoomType.CLASSROOM,
    SubjectType.TUTORIAL: RoomType.CLASSROOM,
    SubjectType.PROJECT: RoomType.CLASSROOM,
    SubjectType.LIBRARY: RoomType.SEMINAR_HALL,
    SubjectType.SPORTS: RoomType.CLASSROOM,
    SubjectType.MENTORING: RoomType.CLASSROOM,
    SubjectType.OPEN_ELECTIVE: RoomType.CLASSROOM,
    SubjectType.PROFESSIONAL_ELECTIVE: RoomType.CLASSROOM,
    SubjectType.LAB: RoomType.LAB,
}


def _resolve_time_structure_id(section: Section, default_structure_id: int) -> int:
    if section.time_structure_id:
        return section.time_structure_id
    if section.program.time_structure_id:
        return section.program.time_structure_id
    return default_structure_id


def _eligible_teacher_ids(db: Session, subject_id: int) -> tuple[int, ...]:
    rows = db.query(TeacherSubject.teacher_id).filter(TeacherSubject.subject_id == subject_id).all()
    return tuple(sorted({r[0] for r in rows}))


def _eligible_room_ids(db: Session, room_type: RoomType, capacity_required: int,
                        lab_category: str | None = None) -> tuple[int, ...]:
    q = db.query(Room.id).filter(Room.room_type == room_type, Room.capacity >= capacity_required)
    if lab_category:
        q = q.filter(Room.lab_category == lab_category)
    return tuple(sorted({r[0] for r in q.all()}))


def _default_structure(db: Session) -> TimeStructure:
    structure = db.query(TimeStructure).filter(TimeStructure.is_default.is_(True)).first()
    if structure is None:
        structure = db.query(TimeStructure).first()
    if structure is None:
        raise ValueError("No TimeStructure configured")
    return structure


def build_grids(db: Session) -> dict[int, TimeGrid]:
    structures = db.query(TimeStructure).all()
    return {s.id: TimeGrid(s) for s in structures}


def _build_regular_and_lab_groups(db: Session, default_structure_id: int) -> list[RequirementGroup]:
    allocations = db.query(Allocation).all()
    buckets: dict[tuple[int, int], list[Allocation]] = defaultdict(list)
    for a in allocations:
        buckets[(a.subject_id, a.section_id)].append(a)

    groups: list[RequirementGroup] = []
    for (subject_id, section_id), allocs in buckets.items():
        subject = allocs[0].subject
        section = allocs[0].section
        structure_id = _resolve_time_structure_id(section, default_structure_id)
        parts = []
        for a in allocs:
            room_type = SUBJECT_ROOM_TYPE.get(subject.subject_type, RoomType.CLASSROOM)
            capacity = a.lab_batch.strength if a.lab_batch_id else section.strength
            if a.is_fixed_teacher and a.teacher_id:
                teacher_opts = (a.teacher_id,)
            else:
                teacher_opts = _eligible_teacher_ids(db, subject_id)
            if a.is_fixed_room and a.room_id:
                room_opts = (a.room_id,)
            else:
                room_opts = _eligible_room_ids(db, room_type, capacity)
            key = f"batch_{a.lab_batch_id}" if a.lab_batch_id else "main"
            parts.append(ReqPart(
                key=key, subject_id=subject_id, teacher_options=teacher_opts,
                is_fixed_teacher=a.is_fixed_teacher, room_type_required=room_type,
                capacity_required=capacity, room_options=room_opts, is_fixed_room=a.is_fixed_room,
                lab_batch_id=a.lab_batch_id,
            ))
        kind = "lab" if subject.is_lab else "regular"
        groups.append(RequirementGroup(
            id=f"alloc_{subject_id}_{section_id}",
            kind=kind,
            label=f"{subject.code} / {section.display_name}",
            subject_id=subject_id,
            occupied_section_ids=(section_id,),
            parts=tuple(parts),
            sessions_per_week=subject.sessions_per_week,
            block_size=subject.block_size,
            spread_across_days=subject.spread_across_days,
            max_per_day=subject.max_per_day,
            time_structure_id=structure_id,
            avoid_last_period=subject.avoid_last_period,
            prefer_afternoon=subject.prefer_afternoon,
            afternoon_cutoff_period=_afternoon_cutoff(db, structure_id),
            source_ref={"type": "allocation", "subject_id": subject_id, "section_id": section_id,
                        "allocation_ids": [a.id for a in allocs]},
        ))
    return groups


_AFTERNOON_CACHE: dict[int, int | None] = {}


def _afternoon_cutoff(db: Session, structure_id: int) -> int | None:
    if structure_id in _AFTERNOON_CACHE:
        return _AFTERNOON_CACHE[structure_id]
    structure = db.get(TimeStructure, structure_id)
    teaching = [p for p in sorted(structure.periods, key=lambda p: p.period_index)]
    teaching_only = [p for p in teaching if p.kind.value == "teaching"]
    cutoff = teaching_only[len(teaching_only) // 2].period_index if teaching_only else None
    _AFTERNOON_CACHE[structure_id] = cutoff
    return cutoff


def _build_combined_groups(db: Session, default_structure_id: int) -> list[RequirementGroup]:
    groups = []
    for cc in db.query(CombinedClass).all():
        section_links = db.query(CombinedClassSection).filter(CombinedClassSection.combined_class_id == cc.id).all()
        section_ids = tuple(sorted({sl.section_id for sl in section_links}))
        if not section_ids:
            continue
        sections = db.query(Section).filter(Section.id.in_(section_ids)).all()
        total_strength = sum(s.strength for s in sections)
        structure_id = _resolve_time_structure_id(sections[0], default_structure_id)
        if cc.teacher_id:
            teacher_opts = (cc.teacher_id,)
            is_fixed_teacher = True
        else:
            teacher_opts = _eligible_teacher_ids(db, cc.subject_id)
            is_fixed_teacher = False
        room_opts = _eligible_room_ids(db, cc.room_type_required, total_strength)
        part = ReqPart(
            key="main", subject_id=cc.subject_id, teacher_options=teacher_opts,
            is_fixed_teacher=is_fixed_teacher, room_type_required=cc.room_type_required,
            capacity_required=total_strength, room_options=room_opts, is_fixed_room=False,
        )
        groups.append(RequirementGroup(
            id=f"combined_{cc.id}", kind="combined", label=cc.name, subject_id=cc.subject_id,
            occupied_section_ids=section_ids, parts=(part,), sessions_per_week=cc.sessions_per_week,
            block_size=cc.block_size, spread_across_days=True, max_per_day=1,
            time_structure_id=structure_id,
            source_ref={"type": "combined", "combined_class_id": cc.id},
        ))
    return groups


def _build_elective_groups(db: Session, default_structure_id: int) -> list[RequirementGroup]:
    groups = []
    for basket in db.query(ElectiveBasket).all():
        participations = db.query(ElectiveParticipation).filter(ElectiveParticipation.basket_id == basket.id).all()
        section_ids = tuple(sorted({p.section_id for p in participations}))
        if not section_ids:
            continue
        sections = db.query(Section).filter(Section.id.in_(section_ids)).all()
        structure_id = _resolve_time_structure_id(sections[0], default_structure_id)
        options = db.query(ElectiveOption).filter(ElectiveOption.basket_id == basket.id).all()
        parts = []
        for opt in options:
            if opt.teacher_id:
                teacher_opts, is_fixed_teacher = (opt.teacher_id,), True
            else:
                teacher_opts, is_fixed_teacher = _eligible_teacher_ids(db, opt.subject_id), False
            room_opts = _eligible_room_ids(db, opt.room_type_required, opt.expected_strength)
            parts.append(ReqPart(
                key=f"opt_{opt.id}", subject_id=opt.subject_id, teacher_options=teacher_opts,
                is_fixed_teacher=is_fixed_teacher, room_type_required=opt.room_type_required,
                capacity_required=opt.expected_strength, room_options=room_opts, is_fixed_room=False,
            ))
        if not parts:
            continue
        groups.append(RequirementGroup(
            id=f"elective_{basket.id}", kind="elective", label=basket.name, subject_id=parts[0].subject_id,
            occupied_section_ids=section_ids, parts=tuple(parts), sessions_per_week=basket.sessions_per_week,
            block_size=basket.block_size, spread_across_days=True, max_per_day=1,
            time_structure_id=structure_id,
            source_ref={"type": "elective", "basket_id": basket.id},
        ))
    return groups


def _teacher_constraints(db: Session) -> tuple[set, set, dict, dict, dict, dict, list]:
    teacher_unavailable = set()
    teacher_day_off = set()
    for u in db.query(TeacherUnavailability).all():
        if u.period_index is None:
            teacher_day_off.add((u.teacher_id, u.day_index))
        else:
            teacher_unavailable.add((u.teacher_id, u.day_index, u.period_index))

    max_per_day, max_per_week, max_consec, visiting_days = {}, {}, {}, {}
    for t in db.query(Teacher).all():
        max_per_day[t.id] = t.max_periods_per_day
        max_per_week[t.id] = t.max_periods_per_week
        max_consec[t.id] = t.max_consecutive_periods
        if t.is_visiting and t.visiting_days:
            visiting_days[t.id] = tuple(t.visiting_days)

    preferences = []
    for p in db.query(TeacherPreference).all():
        preferences.append({
            "teacher_id": p.teacher_id, "type": p.preference_type.value,
            "day_index": p.day_index, "weight": p.weight,
        })
    return teacher_unavailable, teacher_day_off, max_per_day, max_per_week, max_consec, visiting_days, preferences


def _room_unavailable(db: Session, grids: dict[int, TimeGrid]) -> set:
    out = set()
    all_slots = set()
    for grid in grids.values():
        for d, p in grid.all_slots():
            all_slots.add((d, p))
    for u in db.query(RoomUnavailability).all():
        if u.period_index is None:
            for d, p in all_slots:
                if d == u.day_index:
                    out.add((u.room_id, d, p))
        else:
            out.add((u.room_id, u.day_index, u.period_index))
    return out


def _existing_sessions_by_group(db: Session, version_id: int) -> dict[str, list[TimetableSession]]:
    sessions = db.query(TimetableSession).filter(TimetableSession.version_id == version_id).all()
    by_group: dict[str, list[TimetableSession]] = defaultdict(list)
    for s in sessions:
        gid = _group_id_for_session(s)
        if gid:
            by_group[gid].append(s)
    for gid in by_group:
        by_group[gid].sort(key=lambda s: (s.day_index, s.period_index))
    return by_group


def _group_id_for_session(s: TimetableSession) -> str | None:
    if s.combined_class_id:
        return f"combined_{s.combined_class_id}"
    if s.elective_basket_id:
        return f"elective_{s.elective_basket_id}"
    if s.allocation_id and s.allocation is not None:
        return f"alloc_{s.allocation.subject_id}_{s.allocation.section_id}"
    return None


def build_solver_input(
    db: Session,
    locked_from_version_id: int | None = None,
    previous_from_version_id: int | None = None,
) -> SolverInput:
    default_structure = _default_structure(db)
    grids = build_grids(db)

    groups = (
        _build_regular_and_lab_groups(db, default_structure.id)
        + _build_combined_groups(db, default_structure.id)
        + _build_elective_groups(db, default_structure.id)
    )

    (teacher_unavailable, teacher_day_off, max_per_day, max_per_week,
     max_consec, visiting_days, preferences) = _teacher_constraints(db)
    room_unavailable = _room_unavailable(db, grids)

    section_max_per_day, section_max_consecutive, section_strengths = {}, {}, {}
    for s in db.query(Section).all():
        section_strengths[s.id] = s.strength
        if s.max_periods_per_day is not None:
            section_max_per_day[s.id] = s.max_periods_per_day
        if s.max_consecutive_periods is not None:
            section_max_consecutive[s.id] = s.max_consecutive_periods

    locks: list[LockedSession] = []
    if locked_from_version_id is not None:
        by_group = _existing_sessions_by_group(db, locked_from_version_id)
        for gid, sessions in by_group.items():
            for occ, s in enumerate(sessions):
                if not s.is_locked:
                    continue
                part_assign = {}
                links = db.query(SessionSection).filter(SessionSection.session_id == s.id).all()
                # single-part regular/lab/combined sessions: whole session is one part ("main" or batch key)
                key = f"batch_{s.lab_batch_id}" if s.lab_batch_id else "main"
                part_assign[key] = (s.teacher_id, s.room_id)
                locks.append(LockedSession(
                    group_id=gid, occurrence=occ, day_index=s.day_index, period_index=s.period_index,
                    part_assignments=part_assign,
                ))

    previous: list[PreviousSession] = []
    if previous_from_version_id is not None:
        by_group = _existing_sessions_by_group(db, previous_from_version_id)
        for gid, sessions in by_group.items():
            for occ, s in enumerate(sessions):
                previous.append(PreviousSession(
                    group_id=gid, occurrence=occ, day_index=s.day_index, period_index=s.period_index,
                ))

    return SolverInput(
        groups=groups,
        time_structures=grids,
        teacher_unavailable=teacher_unavailable,
        teacher_day_off=teacher_day_off,
        room_unavailable=room_unavailable,
        teacher_max_per_day=max_per_day,
        teacher_max_per_week=max_per_week,
        teacher_max_consecutive=max_consec,
        teacher_visiting_days=visiting_days,
        locks=locks,
        previous=previous,
        teacher_preferences=preferences,
        section_strengths=section_strengths,
        section_max_per_day=section_max_per_day,
        section_max_consecutive=section_max_consecutive,
    )
