"""Solver-facing intermediate representation. Deliberately independent of the ORM so the
solver (and the verifier) can be unit tested with plain hand-built instances."""
from dataclasses import dataclass, field

from app.models.enums import RoomType


@dataclass
class ReqPart:
    """One resource-consuming 'thread' within a requirement group's occurrence.

    A plain theory/lab-no-batch requirement has exactly one part. A batched lab has one
    part per batch. An elective basket occurrence has one part per option.
    """
    key: str
    subject_id: int
    teacher_options: tuple[int, ...]
    is_fixed_teacher: bool
    room_type_required: RoomType
    capacity_required: int
    room_options: tuple[int, ...]
    is_fixed_room: bool
    lab_batch_id: int | None = None
    lab_category_required: str | None = None


@dataclass
class RequirementGroup:
    """Everything that must happen simultaneously for one 'occurrence' of a teaching unit."""
    id: str
    kind: str  # "regular" | "lab" | "combined" | "elective"
    label: str
    subject_id: int  # representative subject (for regular/lab/combined); for elective, first option's
    occupied_section_ids: tuple[int, ...]
    parts: tuple[ReqPart, ...]
    sessions_per_week: int
    block_size: int
    spread_across_days: bool
    max_per_day: int
    time_structure_id: int
    allowed_days: tuple[int, ...] | None = None  # None = all days in structure
    avoid_last_period: bool = False
    prefer_afternoon: bool = False
    afternoon_cutoff_period: int | None = None
    source_ref: dict = field(default_factory=dict)


@dataclass
class LockedSession:
    """A previously-decided, pinned placement the solver must respect exactly."""
    group_id: str
    occurrence: int
    day_index: int
    period_index: int
    part_assignments: dict[str, tuple[int | None, int | None]]  # part key -> (teacher_id, room_id)


@dataclass
class PreviousSession:
    """Prior placement used only for the stability (minimal-change) soft penalty."""
    group_id: str
    occurrence: int
    day_index: int
    period_index: int


@dataclass
class SolverInput:
    groups: list[RequirementGroup]
    time_structures: dict[int, object]  # id -> TimeGrid (filled by builder)
    teacher_unavailable: set[tuple[int, int, int]]  # (teacher_id, day, period)
    teacher_day_off: set[tuple[int, int]] = field(default_factory=set)
    room_unavailable: set[tuple[int, int, int]] = field(default_factory=set)
    teacher_max_per_day: dict[int, int] = field(default_factory=dict)
    teacher_max_per_week: dict[int, int] = field(default_factory=dict)
    teacher_max_consecutive: dict[int, int] = field(default_factory=dict)
    teacher_visiting_days: dict[int, tuple[int, ...]] = field(default_factory=dict)
    locks: list[LockedSession] = field(default_factory=list)
    previous: list[PreviousSession] = field(default_factory=list)
    teacher_preferences: list[dict] = field(default_factory=list)
    section_strengths: dict[int, int] = field(default_factory=dict)
    section_max_per_day: dict[int, int] = field(default_factory=dict)
    section_max_consecutive: dict[int, int] = field(default_factory=dict)
