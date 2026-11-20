"""Infeasibility diagnosis: hand-built scenarios with a single known root cause each,
checking that app.solver.diagnosis names the right cause."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
import app.models  # noqa
from app.models.allocation import Allocation
from app.models.college import Department, Program, Section
from app.models.elective import ElectiveBasket, ElectiveParticipation
from app.models.enums import RoomType, SubjectType
from app.models.room import Room
from app.models.structure import PeriodSlot, TimeStructure, WorkingDay
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.solver.diagnosis import run_prechecks


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def basic_structure(db, days=5, periods=5):
    structure = TimeStructure(name="Default", is_default=True)
    db.add(structure)
    db.flush()
    for i in range(days):
        db.add(WorkingDay(time_structure_id=structure.id, day_index=i, name=f"Day{i}", max_period_index=None))
    for p in range(periods):
        db.add(PeriodSlot(time_structure_id=structure.id, period_index=p, label=f"P{p+1}",
                           start_time="09:00", end_time="09:50", kind="teaching", teaching_order=p))
    db.flush()
    return structure


def basic_college(db):
    dept = Department(name="Dept", code="D1")
    db.add(dept)
    db.flush()
    program = Program(department_id=dept.id, name="Prog", code="P1", duration_semesters=6)
    db.add(program)
    db.flush()
    section = Section(program_id=program.id, semester_number=1, name="A", strength=50)
    db.add(section)
    db.flush()
    return dept, program, section


def test_teacher_overcommitted_is_detected():
    db = make_db()
    basic_structure(db, days=5, periods=5)  # 25 periods/week available
    dept, program, section = basic_college(db)
    teacher = Teacher(code="T1", name="Overloaded", department_id=dept.id,
                       max_periods_per_day=6, max_periods_per_week=10, max_consecutive_periods=4)
    db.add(teacher)
    db.flush()
    # Two subjects, 8 periods/week each, both fixed to the same teacher -> needs 16 but capped at 10.
    for i in range(2):
        subj = Subject(code=f"S{i}", name=f"Subject {i}", department_id=dept.id, subject_type=SubjectType.THEORY,
                        periods_per_week=8, sessions_per_week=8, block_size=1, max_per_day=2)
        db.add(subj)
        db.flush()
        db.add(Allocation(subject_id=subj.id, section_id=section.id, teacher_id=teacher.id, is_fixed_teacher=True))
    db.commit()

    findings = run_prechecks(db)
    cats = {f.category for f in findings}
    assert "teacher_overcommitted" in cats
    f = next(f for f in findings if f.category == "teacher_overcommitted")
    assert f.details["required"] == 16
    assert f.details["available"] == 10


def test_lab_capacity_exceeded_is_detected():
    db = make_db()
    basic_structure(db, days=5, periods=3)
    dept, program, section = basic_college(db)
    # Only 1 lab room offering 15 room-periods/week; demand (20) exceeds that.
    db.add(Room(code="L1", name="Lab 1", room_type=RoomType.LAB, capacity=30))
    db.flush()
    for i in range(5):
        subj = Subject(code=f"LAB{i}", name=f"Lab {i}", department_id=dept.id, subject_type=SubjectType.LAB,
                        periods_per_week=4, sessions_per_week=2, block_size=2, max_per_day=1,
                        requires_lab_batches=False)
        db.add(subj)
        db.flush()
        db.add(Allocation(subject_id=subj.id, section_id=section.id))
    db.commit()

    findings = run_prechecks(db)
    cats = {f.category for f in findings}
    assert "lab_capacity_exceeded" in cats


def test_section_overcommitted_is_detected():
    db = make_db()
    basic_structure(db, days=3, periods=3)  # only 9 teaching periods/week
    dept, program, section = basic_college(db)
    for i in range(3):
        subj = Subject(code=f"S{i}", name=f"Subject {i}", department_id=dept.id, subject_type=SubjectType.THEORY,
                        periods_per_week=6, sessions_per_week=6, block_size=1, max_per_day=6)
        db.add(subj)
        db.flush()
        db.add(Allocation(subject_id=subj.id, section_id=section.id))
    db.commit()

    findings = run_prechecks(db)
    cats = {f.category for f in findings}
    assert "section_overcommitted" in cats


def test_elective_block_too_big_is_detected():
    db = make_db()
    basic_structure(db, days=5, periods=3)  # only 3 consecutive teaching periods per day
    dept, program, section = basic_college(db)
    basket = ElectiveBasket(name="Impossible basket", sessions_per_week=1, block_size=5)
    db.add(basket)
    db.flush()
    db.add(ElectiveParticipation(basket_id=basket.id, section_id=section.id))
    db.commit()

    findings = run_prechecks(db)
    cats = {f.category for f in findings}
    assert "elective_no_valid_slot" in cats


if __name__ == "__main__":
    test_teacher_overcommitted_is_detected()
    test_lab_capacity_exceeded_is_detected()
    test_section_overcommitted_is_detected()
    test_elective_block_too_big_is_detected()
    print("OK")
