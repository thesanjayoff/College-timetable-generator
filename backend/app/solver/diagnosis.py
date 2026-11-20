"""Infeasibility / unplaced-session diagnosis. Runs fast, independent pre-checks so the
admin never just sees "no solution" -- and explains any sessions the solver could not
place with plain-English root causes and ranked relaxations."""
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.allocation import Allocation
from app.models.college import LabBatch, Section
from app.models.elective import ElectiveBasket, ElectiveParticipation
from app.models.enums import RoomType, SubjectType
from app.models.room import Room
from app.models.structure import TimeStructure
from app.models.subject import Subject
from app.models.teacher import Teacher, TeacherUnavailability
from app.solver.grid import TimeGrid


@dataclass
class DiagnosisFinding:
    category: str
    message: str
    severity: str = "blocking"  # "blocking" | "warning"
    suggestions: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


def _grid_for(db: Session, structure_id: int) -> TimeGrid:
    structure = db.query(TimeStructure).get(structure_id)
    return TimeGrid(structure)


def _default_structure_id(db: Session) -> int:
    s = db.query(TimeStructure).filter(TimeStructure.is_default.is_(True)).first()
    if s is None:
        s = db.query(TimeStructure).first()
    return s.id


def _section_structure_id(section: Section, default_id: int) -> int:
    return section.time_structure_id or (section.program.time_structure_id if section.program else None) or default_id


def check_teacher_capacity(db: Session) -> list[DiagnosisFinding]:
    findings = []
    default_id = _default_structure_id(db)
    grids: dict[int, TimeGrid] = {}

    demand: dict[int, int] = {}
    for a in db.query(Allocation).all():
        if not a.is_fixed_teacher or not a.teacher_id:
            continue
        subject = a.subject
        periods = subject.sessions_per_week * subject.block_size
        demand[a.teacher_id] = demand.get(a.teacher_id, 0) + periods

    for teacher in db.query(Teacher).all():
        required = demand.get(teacher.id, 0)
        if required == 0:
            continue
        unavailable = db.query(TeacherUnavailability).filter(TeacherUnavailability.teacher_id == teacher.id).all()
        day_off = {u.day_index for u in unavailable if u.period_index is None}
        slot_off = {(u.day_index, u.period_index) for u in unavailable if u.period_index is not None}

        structure_ids = {
            _section_structure_id(a.section, default_id)
            for a in db.query(Allocation).filter(Allocation.teacher_id == teacher.id).all()
        }
        structure_id = next(iter(structure_ids), default_id)
        if structure_id not in grids:
            grids[structure_id] = _grid_for(db, structure_id)
        grid = grids[structure_id]

        available = 0
        for d in grid.day_indices:
            if d in day_off:
                continue
            for p in grid.teaching_periods_for_day(d):
                if (d, p) not in slot_off:
                    available += 1
        available = min(available, teacher.max_periods_per_week)

        if required > available:
            findings.append(DiagnosisFinding(
                category="teacher_overcommitted",
                message=f"{teacher.name} needs {required} periods/week but is available for only "
                         f"{available} (availability and weekly-max combined).",
                suggestions=[
                    f"Increase {teacher.name}'s weekly period limit if realistic",
                    f"Remove one of {teacher.name}'s unavailable days/periods",
                    f"Reassign some of {teacher.name}'s subjects to another eligible teacher",
                    "Hire additional visiting-faculty hours for this subject",
                ],
                details={"teacher_id": teacher.id, "required": required, "available": available},
            ))
    return findings


def check_lab_capacity(db: Session) -> list[DiagnosisFinding]:
    findings = []
    lab_rooms = db.query(Room).filter(Room.room_type == RoomType.LAB).all()
    if not lab_rooms:
        lab_subjects = db.query(Subject).filter(Subject.subject_type == SubjectType.LAB).count()
        if lab_subjects:
            findings.append(DiagnosisFinding(
                category="no_lab_rooms",
                message="There are lab subjects defined but no rooms of type 'lab' exist.",
                suggestions=["Add at least one lab room"],
            ))
        return findings

    default_id = _default_structure_id(db)
    grid = _grid_for(db, default_id)
    teaching_periods_per_week = sum(len(grid.teaching_periods_for_day(d)) for d in grid.day_indices)
    supply = len(lab_rooms) * teaching_periods_per_week

    demand = 0
    allocs = db.query(Allocation).join(Subject, Allocation.subject_id == Subject.id).filter(
        Subject.subject_type == SubjectType.LAB
    ).all()
    for a in allocs:
        demand += a.subject.sessions_per_week * a.subject.block_size

    if demand > supply:
        findings.append(DiagnosisFinding(
            category="lab_capacity_exceeded",
            message=f"Lab demand is {demand} room-periods/week but the {len(lab_rooms)} lab room(s) "
                     f"only offer {supply} room-periods/week.",
            suggestions=[
                "Add another lab room or extend lab room hours",
                "Allow a half-day / full Saturday to add more teaching periods",
                "Split fewer batches, or reduce a lab's weekly periods",
            ],
            details={"demand": demand, "supply": supply},
        ))

    by_section_subject: dict[tuple[int, int], list[Allocation]] = {}
    for a in allocs:
        by_section_subject.setdefault((a.subject_id, a.section_id), []).append(a)
    for (subject_id, section_id), group in by_section_subject.items():
        batch_count = sum(1 for a in group if a.lab_batch_id)
        if batch_count > len(lab_rooms):
            section = group[0].section
            findings.append(DiagnosisFinding(
                category="insufficient_parallel_lab_rooms",
                message=f"{section.display_name}'s lab needs {batch_count} parallel batches but only "
                         f"{len(lab_rooms)} lab room(s) exist college-wide.",
                suggestions=["Add more lab rooms", "Reduce the number of batches for this lab"],
                details={"section_id": section_id, "subject_id": subject_id},
            ))
    return findings


def check_section_capacity(db: Session) -> list[DiagnosisFinding]:
    findings = []
    default_id = _default_structure_id(db)
    demand: dict[int, int] = {}
    for a in db.query(Allocation).all():
        subject = a.subject
        demand[a.section_id] = demand.get(a.section_id, 0) + subject.sessions_per_week * subject.block_size

    grids: dict[int, TimeGrid] = {}
    for section in db.query(Section).all():
        structure_id = _section_structure_id(section, default_id)
        if structure_id not in grids:
            grids[structure_id] = _grid_for(db, structure_id)
        grid = grids[structure_id]
        supply = sum(len(grid.teaching_periods_for_day(d)) for d in grid.day_indices)
        required = demand.get(section.id, 0)
        if required > supply:
            findings.append(DiagnosisFinding(
                category="section_overcommitted",
                message=f"{section.display_name} needs {required} periods/week but its timetable "
                         f"structure only has {supply} teaching periods/week.",
                suggestions=[
                    "Enable Saturday (or a full Saturday instead of half-day)",
                    "Reduce weekly periods for a lighter subject",
                    "Add more periods per day",
                ],
                details={"section_id": section.id, "required": required, "supply": supply},
            ))
    return findings


def check_elective_baskets(db: Session) -> list[DiagnosisFinding]:
    findings = []
    default_id = _default_structure_id(db)
    for basket in db.query(ElectiveBasket).all():
        participations = db.query(ElectiveParticipation).filter(ElectiveParticipation.basket_id == basket.id).all()
        if not participations:
            continue
        sections = [p.section for p in participations]
        structure_id = _section_structure_id(sections[0], default_id)
        grid = _grid_for(db, structure_id)
        total_slots = sum(len(grid.valid_block_starts(d, basket.block_size)) for d in grid.day_indices)
        if total_slots == 0:
            findings.append(DiagnosisFinding(
                category="elective_no_valid_slot",
                message=f"Elective basket '{basket.name}' needs blocks of {basket.block_size} consecutive "
                         f"periods, but no such block exists in the timetable structure.",
                suggestions=["Reduce the basket's block size", "Add more consecutive teaching periods"],
                details={"basket_id": basket.id},
            ))
        elif total_slots < basket.sessions_per_week:
            findings.append(DiagnosisFinding(
                category="elective_too_few_slots",
                message=f"Elective basket '{basket.name}' needs {basket.sessions_per_week} slots/week "
                         f"but only {total_slots} valid slot(s) of the required block size exist.",
                suggestions=["Reduce sessions/week for this basket", "Add more teaching periods"],
                details={"basket_id": basket.id},
            ))
    return findings


def run_prechecks(db: Session) -> list[DiagnosisFinding]:
    findings: list[DiagnosisFinding] = []
    findings += check_teacher_capacity(db)
    findings += check_lab_capacity(db)
    findings += check_section_capacity(db)
    findings += check_elective_baskets(db)
    return findings


def explain_unplaced(db: Session, unplaced_source_refs: list[dict]) -> list[DiagnosisFinding]:
    """Given the solver's unplaced-occurrence source_refs, try to attribute each to a
    precheck finding; fall back to a generic explanation otherwise."""
    prechecks = run_prechecks(db)
    by_section = {f.details.get("section_id"): f for f in prechecks if "section_id" in f.details}
    by_teacher = {f.details.get("teacher_id"): f for f in prechecks if "teacher_id" in f.details}
    by_basket = {f.details.get("basket_id"): f for f in prechecks if "basket_id" in f.details}

    out = []
    for ref in unplaced_source_refs:
        matched = None
        if ref.get("type") == "allocation":
            matched = by_section.get(ref.get("section_id"))
        elif ref.get("type") == "elective":
            matched = by_basket.get(ref.get("basket_id"))
        if matched:
            out.append(matched)
        else:
            out.append(DiagnosisFinding(
                category="unplaced_unattributed",
                message=f"Could not place a required session ({ref}). This is usually caused by "
                         f"a dense local conflict (several resources all busy at the few remaining "
                         f"common slots) rather than a single capacity shortfall.",
                suggestions=["Try increasing the solve time limit", "Relax a soft preference weight",
                             "Review locked sessions near this requirement"],
                details=ref,
            ))
    return out
