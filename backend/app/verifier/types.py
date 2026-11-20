"""Plain data types for the verifier. Deliberately NOT imported from app.solver.* --
the verifier re-derives everything it needs from the database on its own so it shares
no modeling code with the solver."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class VSession:
    id: int
    sync_group: str | None
    day_index: int
    period_index: int
    num_periods: int
    subject_id: int | None
    teacher_id: int | None
    room_id: int | None
    lab_batch_id: int | None
    section_ids: tuple[int, ...]
    kind: str
    allocation_id: int | None = None
    elective_basket_id: int | None = None
    combined_class_id: int | None = None

    def periods(self) -> list[int]:
        return [self.period_index + k for k in range(self.num_periods)]


@dataclass(frozen=True)
class VSubjectReq:
    subject_id: int
    section_id: int
    sessions_per_week: int
    block_size: int
    max_per_day: int
    is_lab: bool
    avoid_last_period: bool
    prefer_afternoon: bool
    subject_type: str = "theory"


@dataclass(frozen=True)
class VPeriodInfo:
    period_index: int
    is_teaching: bool


@dataclass(frozen=True)
class VDayInfo:
    day_index: int
    max_period_index: int | None


@dataclass
class VTimeStructure:
    id: int
    days: list[VDayInfo]
    periods: list[VPeriodInfo]

    def teaching_periods_for_day(self, day_index: int) -> list[int]:
        cutoff = None
        for d in self.days:
            if d.day_index == day_index:
                cutoff = d.max_period_index
        return [p.period_index for p in self.periods if p.is_teaching and (cutoff is None or p.period_index <= cutoff)]

    def last_teaching_period(self, day_index: int) -> int | None:
        periods = self.teaching_periods_for_day(day_index)
        return max(periods) if periods else None

    def first_teaching_period(self, day_index: int) -> int | None:
        periods = self.teaching_periods_for_day(day_index)
        return min(periods) if periods else None


@dataclass
class VTeacherInfo:
    id: int
    max_periods_per_day: int | None
    max_periods_per_week: int | None
    max_consecutive_periods: int | None
    unavailable_slots: set[tuple[int, int]] = field(default_factory=set)  # (day, period)
    day_off: set[int] = field(default_factory=set)
    preferences: list[dict] = field(default_factory=list)


@dataclass
class VRoomInfo:
    id: int
    room_type: str
    capacity: int
    lab_category: str | None
    unavailable_slots: set[tuple[int, int]] = field(default_factory=set)


@dataclass
class VSectionInfo:
    id: int
    strength: int
    structure_id: int
    max_periods_per_day: int | None
    max_consecutive_periods: int | None


@dataclass
class VerifierInput:
    sessions: list[VSession]
    requirements: list[VSubjectReq]
    structures: dict[int, VTimeStructure]
    teachers: dict[int, VTeacherInfo]
    rooms: dict[int, VRoomInfo]
    sections: dict[int, VSectionInfo]
    expected_combined: dict[int, dict]  # combined_class_id -> {sessions_per_week, block_size, section_ids, room_type, capacity}
    expected_elective: dict[int, dict]  # basket_id -> {sessions_per_week, block_size, section_ids, options:[{id,room_type,capacity}]}
    lab_batch_strength: dict[int, int] = field(default_factory=dict)
