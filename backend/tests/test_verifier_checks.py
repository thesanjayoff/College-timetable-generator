"""Hand-built, adversarial unit tests for the independent verifier's hard-constraint
checks (app.verifier.checks) -- no database, no solver, just plain VerifierInput data."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.verifier.checks import check_all
from app.verifier.types import (
    VDayInfo, VPeriodInfo, VRoomInfo, VSectionInfo, VSession, VSubjectReq,
    VTeacherInfo, VTimeStructure, VerifierInput,
)


def make_structure(id_=1, break_at=3, saturday_cutoff=None) -> VTimeStructure:
    days = [VDayInfo(i, saturday_cutoff if i == 5 else None) for i in range(6)]
    periods = []
    idx = 0
    for slot in range(6):
        periods.append(VPeriodInfo(idx, True))
        idx += 1
        if slot == break_at:
            periods.append(VPeriodInfo(idx, False))
            idx += 1
    return VTimeStructure(id=id_, days=days, periods=periods)


def base_input(sessions, requirements=None, teachers=None, rooms=None, sections=None,
                expected_combined=None, expected_elective=None, lab_batch_strength=None) -> VerifierInput:
    structure = make_structure()
    return VerifierInput(
        sessions=sessions, requirements=requirements or [], structures={1: structure},
        teachers=teachers or {}, rooms=rooms or {}, sections=sections or {},
        expected_combined=expected_combined or {}, expected_elective=expected_elective or {},
        lab_batch_strength=lab_batch_strength or {},
    )


def categories(violations):
    return {v.category for v in violations}


def test_teacher_double_booking_detected():
    s1 = VSession(id=1, sync_group=None, day_index=0, period_index=0, num_periods=1, subject_id=1,
                   teacher_id=100, room_id=1, lab_batch_id=None, section_ids=(1,), kind="regular")
    s2 = VSession(id=2, sync_group=None, day_index=0, period_index=0, num_periods=1, subject_id=2,
                   teacher_id=100, room_id=2, lab_batch_id=None, section_ids=(2,), kind="regular")
    data = base_input([s1, s2])
    violations = check_all(data)
    assert "teacher_double_booking" in categories(violations)


def test_room_double_booking_detected():
    s1 = VSession(id=1, sync_group=None, day_index=0, period_index=0, num_periods=1, subject_id=1,
                   teacher_id=1, room_id=50, lab_batch_id=None, section_ids=(1,), kind="regular")
    s2 = VSession(id=2, sync_group=None, day_index=0, period_index=0, num_periods=1, subject_id=2,
                   teacher_id=2, room_id=50, lab_batch_id=None, section_ids=(2,), kind="regular")
    violations = check_all(base_input([s1, s2]))
    assert "room_double_booking" in categories(violations)


def test_section_double_booking_without_sync_exemption():
    s1 = VSession(id=1, sync_group=None, day_index=0, period_index=0, num_periods=1, subject_id=1,
                   teacher_id=1, room_id=1, lab_batch_id=None, section_ids=(10,), kind="regular")
    s2 = VSession(id=2, sync_group=None, day_index=0, period_index=0, num_periods=1, subject_id=2,
                   teacher_id=2, room_id=2, lab_batch_id=None, section_ids=(10,), kind="regular")
    violations = check_all(base_input([s1, s2]))
    assert "section_double_booking" in categories(violations)


def test_section_overlap_exempted_by_matching_sync_group():
    """Two lab batches of the same section, same slot, same sync_group -> not a conflict."""
    s1 = VSession(id=1, sync_group="lab1_0", day_index=0, period_index=0, num_periods=2, subject_id=9,
                   teacher_id=1, room_id=1, lab_batch_id=201, section_ids=(10,), kind="regular")
    s2 = VSession(id=2, sync_group="lab1_0", day_index=0, period_index=0, num_periods=2, subject_id=9,
                   teacher_id=2, room_id=2, lab_batch_id=202, section_ids=(10,), kind="regular")
    violations = check_all(base_input([s1, s2]))
    assert "section_double_booking" not in categories(violations)
    assert "lab_batch_double_booking" not in categories(violations)  # different batch ids


def test_session_count_mismatch_detected():
    s1 = VSession(id=1, sync_group=None, day_index=0, period_index=0, num_periods=1, subject_id=5,
                   teacher_id=1, room_id=1, lab_batch_id=None, section_ids=(10,), kind="regular")
    req = VSubjectReq(subject_id=5, section_id=10, sessions_per_week=3, block_size=1, max_per_day=1,
                       is_lab=False, avoid_last_period=False, prefer_afternoon=False)
    violations = check_all(base_input([s1], requirements=[req]))
    found = [v for v in violations if v.category == "session_count_mismatch"]
    assert len(found) == 1
    assert found[0].details["expected"] == 3 and found[0].details["found"] == 1


def test_room_type_and_capacity_violations():
    req = VSubjectReq(subject_id=5, section_id=10, sessions_per_week=1, block_size=1, max_per_day=1,
                       is_lab=True, avoid_last_period=False, prefer_afternoon=False, subject_type="lab")
    section = VSectionInfo(id=10, strength=40, structure_id=1, max_periods_per_day=None, max_consecutive_periods=None)
    room = VRoomInfo(id=1, room_type="classroom", capacity=20, lab_category=None)  # wrong type, too small
    s1 = VSession(id=1, sync_group=None, day_index=0, period_index=0, num_periods=1, subject_id=5,
                  teacher_id=1, room_id=1, lab_batch_id=None, section_ids=(10,), kind="regular")
    violations = check_all(base_input([s1], requirements=[req], rooms={1: room}, sections={10: section}))
    cats = categories(violations)
    assert "room_type_mismatch" in cats
    assert "room_capacity_exceeded" in cats


def test_non_teaching_period_used():
    section = VSectionInfo(id=10, strength=40, structure_id=1, max_periods_per_day=None, max_consecutive_periods=None)
    # period_index 3 is teaching, 4 is the break (break_at=3 means index 4 is break); use a 2-block starting at 3
    s1 = VSession(id=1, sync_group=None, day_index=0, period_index=3, num_periods=2, subject_id=9,
                  teacher_id=1, room_id=1, lab_batch_id=None, section_ids=(10,), kind="regular")
    violations = check_all(base_input([s1], sections={10: section}))
    assert "non_teaching_period_used" in categories(violations)


def test_teacher_unavailable_slot_flagged():
    teacher = VTeacherInfo(id=1, max_periods_per_day=None, max_periods_per_week=None, max_consecutive_periods=None,
                            unavailable_slots={(0, 0)})
    s1 = VSession(id=1, sync_group=None, day_index=0, period_index=0, num_periods=1, subject_id=1,
                  teacher_id=1, room_id=1, lab_batch_id=None, section_ids=(10,), kind="regular")
    violations = check_all(base_input([s1], teachers={1: teacher}))
    assert "teacher_unavailable" in categories(violations)


def test_teacher_overload_day_and_consecutive():
    teacher = VTeacherInfo(id=1, max_periods_per_day=2, max_periods_per_week=None, max_consecutive_periods=2)
    sessions = [
        VSession(id=i + 1, sync_group=None, day_index=0, period_index=i, num_periods=1, subject_id=1,
                 teacher_id=1, room_id=1, lab_batch_id=None, section_ids=(10,), kind="regular")
        for i in range(3)  # periods 0,1,2 all teaching, 3 in a row -> exceeds max_periods_per_day=2 and consecutive=2
    ]
    violations = check_all(base_input(sessions, teachers={1: teacher}))
    cats = categories(violations)
    assert "teacher_overload_day" in cats
    assert "teacher_too_many_consecutive" in cats


def test_elective_not_synchronized_flagged():
    s1 = VSession(id=1, sync_group="basket1_0", day_index=0, period_index=0, num_periods=1, subject_id=1,
                  teacher_id=1, room_id=1, lab_batch_id=None, section_ids=(10, 11), kind="elective",
                  elective_basket_id=1)
    s2 = VSession(id=2, sync_group="basket1_0", day_index=1, period_index=0, num_periods=1, subject_id=2,
                  teacher_id=2, room_id=2, lab_batch_id=None, section_ids=(10, 11), kind="elective",
                  elective_basket_id=1)  # same sync_group but DIFFERENT day -> not actually synchronized
    violations = check_all(base_input([s1, s2]))
    assert "elective_not_synchronized" in categories(violations)


def test_clean_schedule_has_zero_violations():
    req = VSubjectReq(subject_id=1, section_id=10, sessions_per_week=1, block_size=1, max_per_day=1,
                       is_lab=False, avoid_last_period=False, prefer_afternoon=False)
    section = VSectionInfo(id=10, strength=40, structure_id=1, max_periods_per_day=None, max_consecutive_periods=None)
    room = VRoomInfo(id=1, room_type="classroom", capacity=60, lab_category=None)
    teacher = VTeacherInfo(id=1, max_periods_per_day=6, max_periods_per_week=24, max_consecutive_periods=4)
    s1 = VSession(id=1, sync_group=None, day_index=0, period_index=0, num_periods=1, subject_id=1,
                  teacher_id=1, room_id=1, lab_batch_id=None, section_ids=(10,), kind="regular")
    violations = check_all(base_input([s1], requirements=[req], teachers={1: teacher}, rooms={1: room},
                                       sections={10: section}))
    assert violations == []


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"{name}: OK")
