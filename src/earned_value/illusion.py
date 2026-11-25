"""The illusion detector: weeks the burn chart read healthy while EV read late.

A burn chart gives one cost-only read: is actual spend near the planned baseline?
Expressed against the budget, "within 5% of budget" is the exact phrase a status
report uses. This module asks, for every reporting week, whether that cost-only
read said healthy at the same moment earned value already said the program was
behind. Those weeks are the illusion: a true statement ("spend within 5% of
budget") standing in for a false one ("the program is healthy").

The dollar size of the illusion is the schedule variance in those weeks: the
budgeted value of work that was promised by the baseline and had not been earned,
a number the burn chart cannot show because it never plots earned value.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .config import DEFAULT_TOLERANCES, Tolerances
from .model import EVMResult, WeeklyMetrics


@dataclass(frozen=True)
class WeekVerdict:
    """How one reporting week looks under each read."""

    week: int
    burn_gap_fraction: float  # |AC - PV| / BAC, the cost-only read
    burn_healthy: bool
    spi: float
    cpi: float
    ev_late: bool
    ev_over: bool
    is_illusion: bool
    hidden_slip_dollars: float  # |schedule variance| when the week is an illusion, else 0


@dataclass(frozen=True)
class IllusionSummary:
    """The headline: how many weeks the illusion held and the worst hidden slip."""

    illusion_weeks: int
    first_illusion_week: int | None
    worst_hidden_slip_dollars: float
    worst_hidden_slip_week: int | None
    final_spi: float
    final_cpi: float
    forecast_overrun_dollars: float  # EAC - BAC at the final week, positive = over budget


def classify_week(
    metrics: WeeklyMetrics,
    bac: float,
    tol: Tolerances = DEFAULT_TOLERANCES,
) -> WeekVerdict:
    """Classify one week under the cost-only read and the earned-value read."""

    burn_gap = abs(metrics.actual_cost - metrics.planned_value) / bac
    burn_healthy = burn_gap <= tol.budget_band

    spi, cpi = metrics.spi, metrics.cpi
    ev_late = math.isfinite(spi) and spi < tol.spi_late
    ev_over = math.isfinite(cpi) and cpi < tol.cpi_over
    is_illusion = burn_healthy and ev_late
    hidden = abs(metrics.schedule_variance) if is_illusion else 0.0

    return WeekVerdict(
        week=metrics.week,
        burn_gap_fraction=burn_gap,
        burn_healthy=burn_healthy,
        spi=spi,
        cpi=cpi,
        ev_late=ev_late,
        ev_over=ev_over,
        is_illusion=is_illusion,
        hidden_slip_dollars=hidden,
    )


def classify_program(result: EVMResult, tol: Tolerances = DEFAULT_TOLERANCES) -> list[WeekVerdict]:
    return [classify_week(m, result.bac, tol) for m in result.points]


def summarize(result: EVMResult, tol: Tolerances = DEFAULT_TOLERANCES) -> IllusionSummary:
    """Reduce the weekly verdicts to the headline figures."""

    verdicts = classify_program(result, tol)
    illusions = [v for v in verdicts if v.is_illusion]

    if illusions:
        worst = max(illusions, key=lambda v: v.hidden_slip_dollars)
        worst_dollars = worst.hidden_slip_dollars
        worst_week: int | None = worst.week
        first_week: int | None = illusions[0].week
    else:
        worst_dollars = 0.0
        worst_week = None
        first_week = None

    final = result.final
    overrun = (final.eac - result.bac) if math.isfinite(final.eac) else math.nan

    return IllusionSummary(
        illusion_weeks=len(illusions),
        first_illusion_week=first_week,
        worst_hidden_slip_dollars=worst_dollars,
        worst_hidden_slip_week=worst_week,
        final_spi=final.spi,
        final_cpi=final.cpi,
        forecast_overrun_dollars=overrun,
    )
