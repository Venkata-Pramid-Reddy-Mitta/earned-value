"""The earned-value engine: the decomposition the burn chart cannot do.

A burn chart plots one actual-cost line against one planned-cost line. The gap
between them is a single number, and a single number cannot say whether the
program is under budget (good) or behind schedule (bad). This module computes the
third measure, earned value, which splits that one gap into two:

    actual_cost - planned_value = (actual_cost - earned_value) + (earned_value - planned_value)
                                = (-cost_variance)            + (schedule_variance)

Everything else here (CPI, SPI, EAC, VAC, TCPI) is the standard PMI arithmetic
built on those three cumulative measures. The functions are pure: given the same
tasks they return the same series, independent of thread count or wall clock.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

from .model import EVMResult, Task, WeeklyMetrics, WeeklyPoint


def _cumulative(series: Sequence[float]) -> list[float]:
    running = 0.0
    out: list[float] = []
    for value in series:
        running += value
        out.append(running)
    return out


def aggregate_weekly(tasks: Iterable[Task], planned_weeks: int) -> list[WeeklyPoint]:
    """Roll per-task weekly increments up into cumulative program curves.

    Tasks may have different-length traces (a task that slipped runs more weeks
    than one that did not). The program horizon is the longest trace, never shorter
    than the planned baseline, so a program that overran its schedule still has a
    row for every week it actually ran.
    """

    tasks = list(tasks)
    if not tasks:
        raise ValueError("cannot aggregate an empty task list")
    horizon = max(planned_weeks, max(t.weeks for t in tasks))

    pv = [0.0] * horizon
    ev = [0.0] * horizon
    ac = [0.0] * horizon
    for task in tasks:
        for i in range(task.weeks):
            pv[i] += task.planned_value[i]
            ev[i] += task.earned_value[i]
            ac[i] += task.actual_cost[i]

    cum_pv = _cumulative(pv)
    cum_ev = _cumulative(ev)
    cum_ac = _cumulative(ac)
    return [
        WeeklyPoint(
            week=i + 1,
            planned_value=cum_pv[i],
            earned_value=cum_ev[i],
            actual_cost=cum_ac[i],
        )
        for i in range(horizon)
    ]


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return math.nan
    return numerator / denominator


def metrics_for_point(point: WeeklyPoint, bac: float) -> WeeklyMetrics:
    """Derive every earned-value figure for a single cumulative point.

    Indices are nan where undefined (no spend yet, or no baseline yet) rather than
    silently 1.0, because a fabricated 1.0 reads as "on track" in exactly the early
    weeks where nothing is known. EAC and VAC are nan when CPI is not a positive
    finite number, for the same reason.
    """

    pv, ev, ac = point.planned_value, point.earned_value, point.actual_cost
    cv = ev - ac
    sv = ev - pv
    cpi = _safe_ratio(ev, ac)
    spi = _safe_ratio(ev, pv)

    if math.isfinite(cpi) and cpi > 0:
        eac = bac / cpi
        vac = bac - eac
    else:
        eac = math.nan
        vac = math.nan

    remaining_budget = bac - ac
    tcpi = _safe_ratio(bac - ev, remaining_budget)

    return WeeklyMetrics(
        week=point.week,
        planned_value=pv,
        earned_value=ev,
        actual_cost=ac,
        cost_variance=cv,
        schedule_variance=sv,
        cpi=cpi,
        spi=spi,
        eac=eac,
        vac=vac,
        tcpi=tcpi,
    )


def evaluate_program(tasks: Iterable[Task], bac: float, planned_weeks: int) -> EVMResult:
    """Full evaluation: cumulative curves plus derived metrics for every week."""

    if bac <= 0:
        raise ValueError(f"bac must be positive, got {bac}")
    points = aggregate_weekly(tasks, planned_weeks)
    metrics = tuple(metrics_for_point(p, bac) for p in points)
    return EVMResult(bac=bac, planned_weeks=planned_weeks, points=metrics)
