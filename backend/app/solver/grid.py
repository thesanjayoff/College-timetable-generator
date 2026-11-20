"""Time grid derived from a TimeStructure: which (day, period) slots exist and which
contiguous runs of teaching periods are available for multi-period blocks (labs)."""
from dataclasses import dataclass

from app.models.enums import PeriodKind
from app.models.structure import TimeStructure


@dataclass(frozen=True)
class DaySpec:
    day_index: int
    name: str
    max_period_index: int | None


@dataclass(frozen=True)
class PeriodSpec:
    period_index: int
    kind: PeriodKind
    teaching_order: int | None


class TimeGrid:
    def __init__(self, structure: TimeStructure):
        self.structure_id = structure.id
        self.days: list[DaySpec] = [
            DaySpec(d.day_index, d.name, d.max_period_index) for d in structure.days
        ]
        self.periods: list[PeriodSpec] = [
            PeriodSpec(p.period_index, p.kind, p.teaching_order) for p in structure.periods
        ]
        self.periods.sort(key=lambda p: p.period_index)
        self._teaching_set = {p.period_index for p in self.periods if p.kind == PeriodKind.TEACHING}

    @property
    def day_indices(self) -> list[int]:
        return [d.day_index for d in self.days]

    def is_teaching(self, period_index: int) -> bool:
        return period_index in self._teaching_set

    def max_period_for_day(self, day_index: int) -> int | None:
        for d in self.days:
            if d.day_index == day_index:
                return d.max_period_index
        return None

    def teaching_periods_for_day(self, day_index: int) -> list[int]:
        cutoff = self.max_period_for_day(day_index)
        return [
            p for p in sorted(self._teaching_set)
            if cutoff is None or p <= cutoff
        ]

    def valid_block_starts(self, day_index: int, block_size: int) -> list[int]:
        """Start period_index values where a block of `block_size` consecutive
        teaching periods fits without straddling a break/lunch or the half-day cutoff."""
        teaching = set(self.teaching_periods_for_day(day_index))
        if not teaching:
            return []
        starts = []
        for p in sorted(teaching):
            if all((p + k) in teaching for k in range(block_size)):
                starts.append(p)
        return starts

    def all_slots(self) -> list[tuple[int, int]]:
        """All (day_index, period_index) teaching slots."""
        out = []
        for d in self.day_indices:
            for p in self.teaching_periods_for_day(d):
                out.append((d, p))
        return out

    def last_teaching_period(self, day_index: int) -> int | None:
        periods = self.teaching_periods_for_day(day_index)
        return max(periods) if periods else None

    def first_teaching_period(self, day_index: int) -> int | None:
        periods = self.teaching_periods_for_day(day_index)
        return min(periods) if periods else None
