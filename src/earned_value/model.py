"""The data model, kept separate from the arithmetic.

Three plain structures: a Task (a scoped piece of budgeted work with a planned
window), a WeeklyPoint (one row of the earned-value curves for one reporting
week), and an EVMResult (the whole program's weekly series plus its summary).
Separating the model from evm.py means the engine can be tested against hand-built
points with no generator in the loop, and the generator can be tested without the
engine.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    """A budgeted piece of work with a planned window and an execution trace.

    budget is this task's share of the program's budget at completion. The
    planned window is [planned_start_week, planned_end_week] inclusive. The three
    weekly series (planned_value, earned_value, actual_cost) are incremental
    dollars per week, indexed from week 1, and each is validated at construction
    so a malformed trace is refused at the boundary rather than producing a quietly
    wrong curve.
    """

    task_id: str
    workstream: str
    budget: float
    planned_start_week: int
    planned_end_week: int
    planned_value: tuple[float, ...]
    earned_value: tuple[float, ...]
    actual_cost: tuple[float, ...]

    def __post_init__(self) -> None:
        if self.budget <= 0:
            raise ValueError(f"task {self.task_id}: budget must be positive, got {self.budget}")
        if self.planned_start_week < 1:
            raise ValueError(f"task {self.task_id}: planned_start_week must be >= 1")
        if self.planned_end_week < self.planned_start_week:
            raise ValueError(f"task {self.task_id}: planned_end_week before planned_start_week")
        lengths = {
            len(self.planned_value),
            len(self.earned_value),
            len(self.actual_cost),
        }
        if len(lengths) != 1:
            raise ValueError(f"task {self.task_id}: pv, ev, ac series lengths differ")
        for series, label in (
            (self.planned_value, "planned_value"),
            (self.earned_value, "earned_value"),
            (self.actual_cost, "actual_cost"),
        ):
            if any(x < 0 for x in series):
                raise ValueError(f"task {self.task_id}: {label} has a negative weekly increment")

    @property
    def weeks(self) -> int:
        return len(self.planned_value)


@dataclass(frozen=True)
class WeeklyPoint:
    """The earned-value state at the end of one reporting week.

    All three base measures are cumulative dollars. The derived variances and
    indices are computed in evm.py, not here, so this stays a transparent record.
    """

    week: int
    planned_value: float
    earned_value: float
    actual_cost: float


@dataclass(frozen=True)
class EVMResult:
    """A full program evaluation: the weekly series plus the headline summary."""

    bac: float
    planned_weeks: int
    points: tuple[WeeklyMetrics, ...]

    @property
    def final(self) -> WeeklyMetrics:
        return self.points[-1]


@dataclass(frozen=True)
class WeeklyMetrics:
    """One reporting week with every standard earned-value figure derived.

    cv, sv in dollars; cpi, spi as indices. eac is the independent forecast
    (BAC / CPI); vac = BAC - EAC, negative when the program is forecast to overrun.
    tcpi is the cost efficiency the remaining work must hit to still land on BAC.
    """

    week: int
    planned_value: float
    earned_value: float
    actual_cost: float
    cost_variance: float
    schedule_variance: float
    cpi: float
    spi: float
    eac: float
    vac: float
    tcpi: float
