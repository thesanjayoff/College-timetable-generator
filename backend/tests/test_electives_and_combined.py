"""End-to-end: electives (parallel options shared across sections) and combined classes
(one session shared by several sections) through the real solver + verifier pipeline."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
import app.models  # noqa
from app.models.college import Department, Program, Section
from app.models.structure import TimeStructure, WorkingDay, PeriodSlot
from app.models.subject import Subject
from app.models.teacher import Teacher, TeacherSubject
from app.models.room import Room
from app.models.allocation import Allocation
from app.models.combined import CombinedClass, CombinedClassSection
from app.models.elective import ElectiveBasket, ElectiveOption, ElectiveParticipation
from app.models.enums import SubjectType, RoomType
from app.models.timetable import TimetableVersion
from app.solver.builder import build_solver_input
from app.solver.service import solve, SolveConfig
from app.services.persist import persist_solve_result
from app.verifier.verify import verify_version


def make_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed(db):
    structure = TimeStructure(name="Default", is_default=True)
    db.add(structure)
    db.flush()
    for i, name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri"]):
        db.add(WorkingDay(time_structure_id=structure.id, day_index=i, name=name, max_period_index=None))
    for p in range(5):
        db.add(PeriodSlot(time_structure_id=structure.id, period_index=p, label=f"P{p+1}",
                           start_time="09:00", end_time="09:50", kind="teaching", teaching_order=p))
    db.flush()

    dept = Department(name="Science", code="SCI")
    db.add(dept)
    db.flush()
    program = Program(department_id=dept.id, name="B.Sc", code="BSC", duration_semesters=6)
    db.add(program)
    db.flush()
    sec_a = Section(program_id=program.id, semester_number=1, name="A", strength=50)
    sec_b = Section(program_id=program.id, semester_number=1, name="B", strength=48)
    db.add_all([sec_a, sec_b])
    db.flush()

    phy = Subject(code="PHY", name="Physics", department_id=dept.id, subject_type=SubjectType.THEORY,
                   periods_per_week=1, sessions_per_week=1, block_size=1, max_per_day=1)
    chem = Subject(code="CHEM", name="Chemistry", department_id=dept.id, subject_type=SubjectType.OPEN_ELECTIVE,
                    periods_per_week=1, sessions_per_week=1, block_size=1, max_per_day=1)
    bio = Subject(code="BIO", name="Biology", department_id=dept.id, subject_type=SubjectType.OPEN_ELECTIVE,
                   periods_per_week=1, sessions_per_week=1, block_size=1, max_per_day=1)
    db.add_all([phy, chem, bio])
    db.flush()

    teachers = [Teacher(code=f"T{i}", name=f"Teacher {i}", department_id=dept.id, max_periods_per_day=6,
                         max_periods_per_week=24, max_consecutive_periods=4) for i in range(3)]
    db.add_all(teachers)
    db.flush()
    for t, subj in zip(teachers, [phy, chem, bio]):
        db.add(TeacherSubject(teacher_id=t.id, subject_id=subj.id))
    db.flush()

    rooms = [
        Room(code="C1", name="Classroom 1", room_type=RoomType.CLASSROOM, capacity=100),
        Room(code="C2", name="Classroom 2", room_type=RoomType.CLASSROOM, capacity=100),
        Room(code="SH1", name="Seminar Hall", room_type=RoomType.SEMINAR_HALL, capacity=150),
    ]
    db.add_all(rooms)
    db.flush()

    # Combined class: Physics taught jointly to both sections in one session.
    cc = CombinedClass(name="Joint Physics", subject_id=phy.id, teacher_id=teachers[0].id,
                        sessions_per_week=1, block_size=1, room_type_required=RoomType.SEMINAR_HALL)
    db.add(cc)
    db.flush()
    db.add_all([
        CombinedClassSection(combined_class_id=cc.id, section_id=sec_a.id),
        CombinedClassSection(combined_class_id=cc.id, section_id=sec_b.id),
    ])

    # Elective basket: Chemistry vs Biology, both sections' students split across the two options.
    basket = ElectiveBasket(name="Science Elective", sessions_per_week=1, block_size=1)
    db.add(basket)
    db.flush()
    db.add_all([
        ElectiveOption(basket_id=basket.id, subject_id=chem.id, teacher_id=teachers[1].id,
                       room_type_required=RoomType.CLASSROOM, expected_strength=40),
        ElectiveOption(basket_id=basket.id, subject_id=bio.id, teacher_id=teachers[2].id,
                       room_type_required=RoomType.CLASSROOM, expected_strength=40),
        ElectiveParticipation(basket_id=basket.id, section_id=sec_a.id),
        ElectiveParticipation(basket_id=basket.id, section_id=sec_b.id),
    ])
    db.flush()

    version = TimetableVersion(name="Draft")
    db.add(version)
    db.commit()
    return version.id, sec_a.id, sec_b.id


def test_electives_and_combined_classes_zero_violations():
    db = make_db()
    version_id, sec_a, sec_b = seed(db)

    data = build_solver_input(db)
    kinds = {g.kind for g in data.groups}
    assert "combined" in kinds and "elective" in kinds

    result = solve(data, weights={"section_gaps": 5}, config=SolveConfig(
        time_limit_seconds=15, num_workers=4, deterministic=True, random_seed=1))
    assert result.is_feasible
    assert not result.unplaced, result.unplaced

    persist_solve_result(db, version_id, result)
    report = verify_version(db, version_id)
    if not report.is_clean:
        for v in report.hard_violations:
            print("VIOLATION:", v.category, v.message)
    assert report.is_clean

    from app.models.timetable import SessionSection, TimetableSession
    combined_sessions = db.query(TimetableSession).filter(TimetableSession.combined_class_id.isnot(None)).all()
    assert len(combined_sessions) == 1
    linked = {l.section_id for l in db.query(SessionSection).filter(
        SessionSection.session_id == combined_sessions[0].id).all()}
    assert linked == {sec_a, sec_b}

    elective_sessions = db.query(TimetableSession).filter(TimetableSession.elective_basket_id.isnot(None)).all()
    assert len(elective_sessions) == 2  # one row per option
    slots = {(s.day_index, s.period_index) for s in elective_sessions}
    assert len(slots) == 1, "both elective options must be scheduled at the same slot"


if __name__ == "__main__":
    test_electives_and_combined_classes_zero_violations()
    print("OK")
