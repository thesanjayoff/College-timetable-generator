"""Synthetic Indian-college data generator. Used both for the seeded demo data and for
the scale benchmarks (small/medium/large). Deterministic given a random seed."""
import math
import random
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.allocation import Allocation
from app.models.college import Department, LabBatch, Program, Section
from app.models.combined import CombinedClass, CombinedClassSection
from app.models.elective import ElectiveBasket, ElectiveOption, ElectiveParticipation
from app.models.enums import RoomType, SubjectType
from app.models.room import Room
from app.models.structure import PeriodSlot, TimeStructure, WorkingDay
from app.models.subject import Subject
from app.models.teacher import Teacher, TeacherSubject, TeacherUnavailability, TeacherPreference
from app.models.enums import PreferenceType

DEPARTMENT_NAMES = [
    ("CSE", "Computer Science & Engineering"), ("ECE", "Electronics & Communication"),
    ("MECH", "Mechanical Engineering"), ("CIVIL", "Civil Engineering"),
    ("EEE", "Electrical & Electronics"), ("IT", "Information Technology"),
    ("CHEM", "Chemical Engineering"), ("AERO", "Aeronautical Engineering"),
    ("BME", "Biomedical Engineering"), ("MBA", "Management Studies"),
    ("AIDS", "AI & Data Science"), ("CYS", "Cyber Security"),
]

THEORY_TEMPLATES = ["Mathematics", "Physics / Core Theory", "Programming Fundamentals",
                    "Data Structures", "Analysis & Design", "Communication Skills",
                    "Professional Ethics", "Economics", "Systems Theory"]


@dataclass
class SizeSpec:
    departments: int
    sections: int
    teachers: int
    rooms: int


SIZES = {
    "small": SizeSpec(departments=2, sections=6, teachers=15, rooms=8),
    "medium": SizeSpec(departments=6, sections=25, teachers=80, rooms=40),
    "large": SizeSpec(departments=12, sections=60, teachers=200, rooms=100),
}


def _create_time_structure(db: Session) -> TimeStructure:
    structure = TimeStructure(name="Default", is_default=True)
    db.add(structure)
    db.flush()
    for i, name in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]):
        db.add(WorkingDay(time_structure_id=structure.id, day_index=i, name=name,
                           max_period_index=3 if name == "Saturday" else None))
    idx = 0
    teaching_order = 0
    for slot in range(7):
        db.add(PeriodSlot(time_structure_id=structure.id, period_index=idx, label=f"Period {slot + 1}",
                           start_time=f"{9 + slot}:00", end_time=f"{9 + slot}:50", kind="teaching",
                           teaching_order=teaching_order))
        idx += 1
        teaching_order += 1
        if slot == 3:
            db.add(PeriodSlot(time_structure_id=structure.id, period_index=idx, label="Lunch",
                               start_time="13:00", end_time="13:40", kind="lunch"))
            idx += 1
    db.flush()
    return structure


def generate_college(db: Session, size: str = "medium", seed: int = 42) -> dict:
    rng = random.Random(seed)
    spec = SIZES[size]

    structure = _create_time_structure(db)

    departments = []
    for i in range(spec.departments):
        code, name = DEPARTMENT_NAMES[i % len(DEPARTMENT_NAMES)]
        code = f"{code}{i // len(DEPARTMENT_NAMES) or ''}"
        d = Department(code=code, name=f"{name}")
        db.add(d)
        departments.append(d)
    db.flush()

    programs = []
    for d in departments:
        p = Program(department_id=d.id, name=f"B.Tech {d.name}", code=f"BT{d.code}", duration_semesters=8)
        db.add(p)
        programs.append(p)
    db.flush()

    # --- sections, spread across semesters 1..8 and departments ---
    sections: list[Section] = []
    sections_per_dept = max(1, spec.sections // spec.departments)
    remaining = spec.sections
    for p in programs:
        n = min(remaining, sections_per_dept) if p is not programs[-1] else remaining
        for i in range(n):
            sem = (i % 8) + 1
            label = chr(ord("A") + (i // 8))
            strength = rng.randint(50, 70)
            s = Section(program_id=p.id, semester_number=sem, name=label, strength=strength)
            db.add(s)
            sections.append(s)
        remaining -= n
        if remaining <= 0:
            break
    db.flush()

    # --- subjects per (department, semester) bucket ---
    subjects_by_dept_sem: dict[tuple[int, int], list[Subject]] = {}
    for d, p in zip(departments, programs):
        sems_in_use = sorted({s.semester_number for s in sections if s.program_id == p.id})
        for sem in sems_in_use:
            subs = []
            n_theory = rng.randint(3, 4)
            for i in range(n_theory):
                base = THEORY_TEMPLATES[(sem + i) % len(THEORY_TEMPLATES)]
                code = f"{d.code}{sem}{i + 1}"
                subj = Subject(
                    code=code, name=f"{base} ({d.code} Sem {sem})", department_id=d.id,
                    subject_type=SubjectType.THEORY, credits=rng.choice([3, 4]),
                    periods_per_week=rng.choice([3, 4]), sessions_per_week=rng.choice([3, 4]),
                    block_size=1, spread_across_days=True, max_per_day=1,
                    avoid_last_period=rng.random() < 0.2,
                )
                db.add(subj)
                subs.append(subj)
            lab_code = f"{d.code}{sem}L"
            lab = Subject(
                code=lab_code, name=f"{d.code} Lab (Sem {sem})", department_id=d.id,
                subject_type=SubjectType.LAB, credits=2, periods_per_week=2, sessions_per_week=1,
                block_size=2, spread_across_days=True, max_per_day=1, requires_lab_batches=True,
                prefer_afternoon=rng.random() < 0.5,
            )
            db.add(lab)
            subs.append(lab)
            subjects_by_dept_sem[(d.id, sem)] = subs
    db.flush()

    # --- teachers ---
    teachers: list[Teacher] = []
    teachers_per_dept = max(2, spec.teachers // spec.departments)
    remaining_t = spec.teachers
    for di, d in enumerate(departments):
        n = min(remaining_t, teachers_per_dept) if d is not departments[-1] else remaining_t
        for i in range(n):
            is_visiting = rng.random() < 0.08
            t = Teacher(
                code=f"{d.code}-T{i + 1:03d}", name=f"Dr. {d.code} Faculty {i + 1}", department_id=d.id,
                max_periods_per_day=rng.choice([5, 6, 6, 7]), max_periods_per_week=rng.choice([20, 22, 24]),
                max_consecutive_periods=rng.choice([3, 4]), is_visiting=is_visiting,
                visiting_days=[0, 2, 4] if is_visiting else None,
            )
            db.add(t)
            teachers.append(t)
        remaining_t -= n
        if remaining_t <= 0:
            break
    db.flush()
    teachers_by_dept: dict[int, list[Teacher]] = {}
    for t in teachers:
        teachers_by_dept.setdefault(t.department_id, []).append(t)

    for t in teachers:
        dept_subjects = [s for (did, sem), subs in subjects_by_dept_sem.items() if did == t.department_id for s in subs]
        if not dept_subjects:
            continue
        choices = rng.sample(dept_subjects, k=min(len(dept_subjects), rng.randint(2, 4)))
        for subj in choices:
            db.add(TeacherSubject(teacher_id=t.id, subject_id=subj.id))
        if rng.random() < 0.3:
            day_off = rng.randint(0, 5)
            db.add(TeacherUnavailability(teacher_id=t.id, day_index=day_off, period_index=None))
            db.add(TeacherPreference(teacher_id=t.id, preference_type=PreferenceType.FREE_DAY,
                                      day_index=day_off, weight=1.0))
        if rng.random() < 0.2:
            db.add(TeacherPreference(teacher_id=t.id, preference_type=PreferenceType.NO_FIRST_PERIOD,
                                      day_index=None, weight=1.0))
    db.flush()

    # --- rooms ---
    rooms: list[Room] = []
    n_classrooms = int(spec.rooms * 0.6)
    n_labs = int(spec.rooms * 0.3)
    n_seminar = spec.rooms - n_classrooms - n_labs
    for i in range(n_classrooms):
        rooms.append(Room(code=f"CR{i + 1:03d}", name=f"Classroom {i + 1}", room_type=RoomType.CLASSROOM,
                           capacity=rng.choice([60, 70, 80]), building=f"Block {chr(ord('A') + i % 4)}",
                           floor=rng.randint(0, 4)))
    for i in range(n_labs):
        rooms.append(Room(code=f"LB{i + 1:03d}", name=f"Lab {i + 1}", room_type=RoomType.LAB,
                           capacity=rng.choice([30, 35, 40]), lab_category=rng.choice(["computer", "core", "electronics"]),
                           building=f"Lab Block", floor=rng.randint(0, 2)))
    for i in range(max(1, n_seminar)):
        rooms.append(Room(code=f"SH{i + 1:03d}", name=f"Seminar Hall {i + 1}", room_type=RoomType.SEMINAR_HALL,
                           capacity=rng.choice([120, 150, 200]), building="Main Block", floor=0))
    db.add_all(rooms)
    db.flush()
    lab_rooms = [r for r in rooms if r.room_type == RoomType.LAB]

    # --- allocations (+ lab batches) ---
    for sec in sections:
        subs = subjects_by_dept_sem.get((sec.program.department_id, sec.semester_number), [])
        for subj in subs:
            eligible = [t for t in teachers_by_dept.get(sec.program.department_id, [])
                        if db.query(TeacherSubject).filter(
                            TeacherSubject.teacher_id == t.id, TeacherSubject.subject_id == subj.id).first()]
            if subj.subject_type == SubjectType.LAB:
                n_batches = max(1, math.ceil(sec.strength / 30))
                for bi in range(n_batches):
                    batch = LabBatch(section_id=sec.id, name=f"{sec.name}{bi + 1}",
                                      strength=math.ceil(sec.strength / n_batches))
                    db.add(batch)
                    db.flush()
                    teacher = rng.choice(eligible) if eligible and rng.random() < 0.85 else None
                    db.add(Allocation(subject_id=subj.id, section_id=sec.id, lab_batch_id=batch.id,
                                       teacher_id=teacher.id if teacher else None,
                                       is_fixed_teacher=teacher is not None))
            else:
                teacher = rng.choice(eligible) if eligible and rng.random() < 0.8 else None
                db.add(Allocation(subject_id=subj.id, section_id=sec.id,
                                   teacher_id=teacher.id if teacher else None,
                                   is_fixed_teacher=teacher is not None))
    db.flush()

    # --- a couple of elective baskets across same-semester sections ---
    created_baskets = 0
    sem_groups: dict[int, list[Section]] = {}
    for s in sections:
        sem_groups.setdefault(s.semester_number, []).append(s)
    for sem, secs in sem_groups.items():
        if len(secs) < 2 or created_baskets >= 2:
            continue
        participants = secs[:min(len(secs), 3)]
        basket = ElectiveBasket(name=f"Open Elective Sem {sem}", sessions_per_week=2, block_size=1)
        db.add(basket)
        db.flush()
        participant_subject_ids = {
            s.id for sec in participants for s in subjects_by_dept_sem.get((sec.program.department_id, sec.semester_number), [])
        }
        all_theory = [
            s for subs in subjects_by_dept_sem.values() for s in subs
            if s.subject_type == SubjectType.THEORY and s.id not in participant_subject_ids
        ]
        if not all_theory:
            continue
        options = rng.sample(all_theory, k=min(3, len(all_theory)))
        for opt_subj in options:
            db.add(ElectiveOption(basket_id=basket.id, subject_id=opt_subj.id, room_type_required=RoomType.CLASSROOM,
                                   expected_strength=rng.randint(20, 35)))
        for sec in participants:
            db.add(ElectiveParticipation(basket_id=basket.id, section_id=sec.id))
        created_baskets += 1
    db.flush()

    # --- one combined class for first-semester sections across departments ---
    first_sem_sections = [s for s in sections if s.semester_number == 1]
    if len(first_sem_sections) >= 2:
        common_subject = Subject(
            code="COMMON101", name="Engineering Foundations (Common)", department_id=departments[0].id,
            subject_type=SubjectType.THEORY, credits=2, periods_per_week=1, sessions_per_week=1, block_size=1,
            spread_across_days=False, max_per_day=1,
        )
        db.add(common_subject)
        db.flush()
        cc = CombinedClass(name="First Year Foundations", subject_id=common_subject.id, sessions_per_week=1,
                            block_size=1, room_type_required=RoomType.SEMINAR_HALL)
        db.add(cc)
        db.flush()
        for sec in first_sem_sections[:6]:
            db.add(CombinedClassSection(combined_class_id=cc.id, section_id=sec.id))
    db.commit()

    return {
        "departments": len(departments), "programs": len(programs), "sections": len(sections),
        "teachers": len(teachers), "rooms": len(rooms),
        "subjects": sum(len(v) for v in subjects_by_dept_sem.values()),
    }


if __name__ == "__main__":
    import sys

    from app.database import Base, SessionLocal, engine
    import app.models  # noqa

    size = sys.argv[1] if len(sys.argv) > 1 else "medium"
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        stats = generate_college(db, size=size)
        print(f"Generated '{size}' college: {stats}")
    finally:
        db.close()
