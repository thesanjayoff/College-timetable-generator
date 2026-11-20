"""End-to-end: seed a tiny college in SQLite, solve, persist, and run the independent
verifier. This is the main smoke test that the whole pipeline is wired correctly."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
import app.models  # noqa: registers all tables
from app.models.college import Department, Program, Section, LabBatch
from app.models.structure import TimeStructure, WorkingDay, PeriodSlot
from app.models.subject import Subject
from app.models.teacher import Teacher, TeacherSubject
from app.models.room import Room
from app.models.allocation import Allocation
from app.models.enums import SubjectType, RoomType
from app.models.timetable import TimetableVersion
from app.solver.builder import build_solver_input
from app.solver.service import solve, SolveConfig
from app.services.persist import persist_solve_result
from app.verifier.verify import verify_version


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def seed(db):
    structure = TimeStructure(name="Default", is_default=True)
    db.add(structure)
    db.flush()
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    for i, name in enumerate(days):
        db.add(WorkingDay(time_structure_id=structure.id, day_index=i, name=name,
                           max_period_index=3 if name == "Sat" else None))
    idx = 0
    for slot in range(7):
        db.add(PeriodSlot(time_structure_id=structure.id, period_index=idx, label=f"P{slot+1}",
                           start_time="09:00", end_time="10:00", kind="teaching", teaching_order=slot))
        idx += 1
        if slot == 3:
            db.add(PeriodSlot(time_structure_id=structure.id, period_index=idx, label="Lunch",
                               start_time="13:00", end_time="13:40", kind="lunch"))
            idx += 1
    db.flush()

    dept = Department(name="Computer Science", code="CSE")
    db.add(dept)
    db.flush()
    program = Program(department_id=dept.id, name="B.Tech CSE", code="BTCSE", duration_semesters=8)
    db.add(program)
    db.flush()

    sec_a = Section(program_id=program.id, semester_number=3, name="A", strength=60)
    sec_b = Section(program_id=program.id, semester_number=3, name="B", strength=58)
    db.add_all([sec_a, sec_b])
    db.flush()
    batch_a1 = LabBatch(section_id=sec_a.id, name="A1", strength=30)
    batch_a2 = LabBatch(section_id=sec_a.id, name="A2", strength=30)
    batch_b1 = LabBatch(section_id=sec_b.id, name="B1", strength=29)
    batch_b2 = LabBatch(section_id=sec_b.id, name="B2", strength=29)
    db.add_all([batch_a1, batch_a2, batch_b1, batch_b2])
    db.flush()

    maths = Subject(code="MA301", name="Maths III", department_id=dept.id, subject_type=SubjectType.THEORY,
                     credits=4, periods_per_week=4, sessions_per_week=4, block_size=1, max_per_day=1)
    dsa = Subject(code="CS301", name="Data Structures", department_id=dept.id, subject_type=SubjectType.THEORY,
                  credits=3, periods_per_week=3, sessions_per_week=3, block_size=1, max_per_day=1)
    dsa_lab = Subject(code="CS301L", name="DS Lab", department_id=dept.id, subject_type=SubjectType.LAB,
                       credits=2, periods_per_week=2, sessions_per_week=1, block_size=2, max_per_day=1,
                       requires_lab_batches=True, prefer_afternoon=True)
    db.add_all([maths, dsa, dsa_lab])
    db.flush()

    teachers = [Teacher(code=f"T{i}", name=f"Teacher {i}", department_id=dept.id,
                         max_periods_per_day=6, max_periods_per_week=24, max_consecutive_periods=4)
                for i in range(1, 6)]
    db.add_all(teachers)
    db.flush()
    for t in teachers:
        for subj in (maths, dsa, dsa_lab):
            db.add(TeacherSubject(teacher_id=t.id, subject_id=subj.id))
    db.flush()

    rooms = [
        Room(code="C1", name="Classroom 1", room_type=RoomType.CLASSROOM, capacity=70),
        Room(code="C2", name="Classroom 2", room_type=RoomType.CLASSROOM, capacity=70),
        Room(code="L1", name="Lab 1", room_type=RoomType.LAB, capacity=35),
        Room(code="L2", name="Lab 2", room_type=RoomType.LAB, capacity=35),
    ]
    db.add_all(rooms)
    db.flush()

    for sec in (sec_a, sec_b):
        db.add(Allocation(subject_id=maths.id, section_id=sec.id, teacher_id=teachers[0].id, is_fixed_teacher=True))
        db.add(Allocation(subject_id=dsa.id, section_id=sec.id, teacher_id=teachers[1].id, is_fixed_teacher=True))
    db.add(Allocation(subject_id=dsa_lab.id, section_id=sec_a.id, lab_batch_id=batch_a1.id,
                       teacher_id=teachers[2].id, is_fixed_teacher=True))
    db.add(Allocation(subject_id=dsa_lab.id, section_id=sec_a.id, lab_batch_id=batch_a2.id,
                       teacher_id=teachers[3].id, is_fixed_teacher=True))
    db.add(Allocation(subject_id=dsa_lab.id, section_id=sec_b.id, lab_batch_id=batch_b1.id,
                       teacher_id=teachers[2].id, is_fixed_teacher=True))
    db.add(Allocation(subject_id=dsa_lab.id, section_id=sec_b.id, lab_batch_id=batch_b2.id,
                       teacher_id=teachers[3].id, is_fixed_teacher=True))
    db.flush()

    version = TimetableVersion(name="Draft 1")
    db.add(version)
    db.commit()
    return version.id


def test_pipeline_zero_hard_violations():
    db = make_db()
    version_id = seed(db)

    data = build_solver_input(db)
    assert len(data.groups) == 6  # 2 theory x2 sections + 1 lab group x2 sections

    result = solve(data, weights={"section_gaps": 10, "teacher_gaps": 5, "lab_afternoon_preference": 4},
                    config=SolveConfig(time_limit_seconds=20, num_workers=4, deterministic=True, random_seed=1))
    assert result.is_feasible, result.status
    assert not result.unplaced, result.unplaced

    persist_solve_result(db, version_id, result)

    report = verify_version(db, version_id)
    if not report.is_clean:
        for v in report.hard_violations:
            print("VIOLATION:", v.category, v.message)
    assert report.is_clean
    print("Scorecard:", report.scorecard)


if __name__ == "__main__":
    test_pipeline_zero_hard_violations()
    print("OK")
