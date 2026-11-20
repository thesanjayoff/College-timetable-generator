"""Loads a VerifierInput directly from the database. Written independently of
app.solver.builder on purpose (see app/verifier/types.py docstring)."""
from sqlalchemy.orm import Session

from app.models.allocation import Allocation
from app.models.college import LabBatch, Section
from app.models.combined import CombinedClass, CombinedClassSection
from app.models.elective import ElectiveBasket, ElectiveOption, ElectiveParticipation
from app.models.room import Room, RoomUnavailability
from app.models.structure import TimeStructure
from app.models.teacher import Teacher, TeacherPreference, TeacherUnavailability
from app.models.timetable import SessionSection, TimetableSession
from app.verifier.types import (
    VDayInfo, VPeriodInfo, VRoomInfo, VSectionInfo, VSession, VSubjectReq,
    VTeacherInfo, VTimeStructure, VerifierInput,
)


def _load_structures(db: Session) -> dict[int, VTimeStructure]:
    out = {}
    for s in db.query(TimeStructure).all():
        days = [VDayInfo(d.day_index, d.max_period_index) for d in s.days]
        periods = [VPeriodInfo(p.period_index, p.kind.value == "teaching") for p in s.periods]
        out[s.id] = VTimeStructure(id=s.id, days=days, periods=periods)
    return out


def _load_teachers(db: Session) -> dict[int, VTeacherInfo]:
    out: dict[int, VTeacherInfo] = {}
    for t in db.query(Teacher).all():
        out[t.id] = VTeacherInfo(
            id=t.id, max_periods_per_day=t.max_periods_per_day,
            max_periods_per_week=t.max_periods_per_week,
            max_consecutive_periods=t.max_consecutive_periods,
        )
    for u in db.query(TeacherUnavailability).all():
        info = out.get(u.teacher_id)
        if info is None:
            continue
        if u.period_index is None:
            info.day_off.add(u.day_index)
        else:
            info.unavailable_slots.add((u.day_index, u.period_index))
    for p in db.query(TeacherPreference).all():
        info = out.get(p.teacher_id)
        if info is None:
            continue
        info.preferences.append({"type": p.preference_type.value, "day_index": p.day_index, "weight": p.weight})
    return out


def _load_rooms(db: Session) -> dict[int, VRoomInfo]:
    out: dict[int, VRoomInfo] = {}
    for r in db.query(Room).all():
        out[r.id] = VRoomInfo(id=r.id, room_type=r.room_type.value, capacity=r.capacity, lab_category=r.lab_category)
    for u in db.query(RoomUnavailability).all():
        info = out.get(u.room_id)
        if info is None:
            continue
        if u.period_index is not None:
            info.unavailable_slots.add((u.day_index, u.period_index))
    return out


def _load_sections(db: Session, default_structure_id: int) -> dict[int, VSectionInfo]:
    out = {}
    for s in db.query(Section).all():
        structure_id = s.time_structure_id or (s.program.time_structure_id if s.program else None) or default_structure_id
        out[s.id] = VSectionInfo(
            id=s.id, strength=s.strength, structure_id=structure_id,
            max_periods_per_day=s.max_periods_per_day, max_consecutive_periods=s.max_consecutive_periods,
        )
    return out


def _load_requirements(db: Session) -> list[VSubjectReq]:
    out = []
    seen = set()
    for a in db.query(Allocation).all():
        key = (a.subject_id, a.section_id)
        if key in seen:
            continue
        seen.add(key)
        subj = a.subject
        out.append(VSubjectReq(
            subject_id=a.subject_id, section_id=a.section_id, sessions_per_week=subj.sessions_per_week,
            block_size=subj.block_size, max_per_day=subj.max_per_day, is_lab=subj.is_lab,
            avoid_last_period=subj.avoid_last_period, prefer_afternoon=subj.prefer_afternoon,
            subject_type=subj.subject_type.value,
        ))
    return out


def _load_lab_batch_strength(db: Session) -> dict[int, int]:
    return {b.id: b.strength for b in db.query(LabBatch).all()}


def _load_expected_combined(db: Session) -> dict[int, dict]:
    out = {}
    for cc in db.query(CombinedClass).all():
        links = db.query(CombinedClassSection).filter(CombinedClassSection.combined_class_id == cc.id).all()
        sections = db.query(Section).filter(Section.id.in_([l.section_id for l in links])).all()
        out[cc.id] = {
            "sessions_per_week": cc.sessions_per_week, "block_size": cc.block_size,
            "section_ids": tuple(sorted(l.section_id for l in links)),
            "room_type": cc.room_type_required.value,
            "capacity": sum(s.strength for s in sections),
        }
    return out


def _load_expected_elective(db: Session) -> dict[int, dict]:
    out = {}
    for basket in db.query(ElectiveBasket).all():
        participations = db.query(ElectiveParticipation).filter(ElectiveParticipation.basket_id == basket.id).all()
        options = db.query(ElectiveOption).filter(ElectiveOption.basket_id == basket.id).all()
        out[basket.id] = {
            "sessions_per_week": basket.sessions_per_week, "block_size": basket.block_size,
            "section_ids": tuple(sorted(p.section_id for p in participations)),
            "options": [
                {"id": o.id, "room_type": o.room_type_required.value, "capacity": o.expected_strength,
                 "subject_id": o.subject_id}
                for o in options
            ],
        }
    return out


def _load_sessions(db: Session, version_id: int) -> list[VSession]:
    rows = db.query(TimetableSession).filter(TimetableSession.version_id == version_id).all()
    links = db.query(SessionSection).filter(
        SessionSection.session_id.in_([r.id for r in rows])
    ).all() if rows else []
    section_map: dict[int, list[int]] = {}
    for link in links:
        section_map.setdefault(link.session_id, []).append(link.section_id)

    out = []
    for r in rows:
        out.append(VSession(
            id=r.id, sync_group=r.sync_group, day_index=r.day_index, period_index=r.period_index,
            num_periods=r.num_periods, subject_id=r.subject_id, teacher_id=r.teacher_id, room_id=r.room_id,
            lab_batch_id=r.lab_batch_id, section_ids=tuple(sorted(section_map.get(r.id, []))),
            kind=r.session_kind.value, allocation_id=r.allocation_id,
            elective_basket_id=r.elective_basket_id, combined_class_id=r.combined_class_id,
        ))
    return out


def build_verifier_input(db: Session, version_id: int) -> VerifierInput:
    default_structure = db.query(TimeStructure).filter(TimeStructure.is_default.is_(True)).first()
    default_id = default_structure.id if default_structure else db.query(TimeStructure).first().id
    return VerifierInput(
        sessions=_load_sessions(db, version_id),
        requirements=_load_requirements(db),
        structures=_load_structures(db),
        teachers=_load_teachers(db),
        rooms=_load_rooms(db),
        sections=_load_sections(db, default_id),
        expected_combined=_load_expected_combined(db),
        expected_elective=_load_expected_elective(db),
        lab_batch_strength=_load_lab_batch_strength(db),
    )
