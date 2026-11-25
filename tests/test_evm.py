"""The earned-value arithmetic.

These tests fix the standard PMI definitions against small hand-built inputs so a
reviewer can read the expected numbers without a spreadsheet, and they pin the one
identity the whole project rests on: the spend gap decomposes into a schedule part
and a cost part.
"""

from __future__ import annotations

import math

import pytest

from earned_value.evm import aggregate_weekly, evaluate_program, metrics_for_point
from earned_value.model import Task, WeeklyPoint


def _task(pv, ev, ac, start=1, end=None, budget=None) -> Task:
    end = end if end is not None else len(pv)
    budget = budget if budget is not None else float(sum(pv))
    return Task(
        task_id="T",
        workstream="ws",
        budget=budget,
        planned_start_week=start,
        planned_end_week=end,
        planned_value=tuple(float(x) for x in pv),
        earned_value=tuple(float(x) for x in ev),
        actual_cost=tuple(float(x) for x in ac),
    )


def _m(pv, ev, ac, bac):
    point = WeeklyPoint(1, planned_value=pv, earned_value=ev, actual_cost=ac)
    return metrics_for_point(point, bac=bac)


def test_aggregate_rejects_an_empty_task_list():
    with pytest.raises(ValueError, match="empty task list"):
        aggregate_weekly([], planned_weeks=4)


def test_aggregate_produces_cumulative_planned_value():
    points = aggregate_weekly([_task([10, 10, 10], [10, 10, 10], [10, 10, 10])], planned_weeks=3)
    assert [p.planned_value for p in points] == [10.0, 20.0, 30.0]


def test_aggregate_produces_cumulative_earned_value():
    points = aggregate_weekly([_task([10, 10, 10], [8, 8, 8], [11, 11, 11])], planned_weeks=3)
    assert [p.earned_value for p in points] == [8.0, 16.0, 24.0]


def test_aggregate_produces_cumulative_actual_cost():
    points = aggregate_weekly([_task([10, 10], [9, 9], [12, 12])], planned_weeks=2)
    assert [p.actual_cost for p in points] == [12.0, 24.0]


def test_aggregate_sums_two_tasks_week_by_week():
    a = _task([10, 10], [10, 10], [10, 10])
    b = _task([5, 5], [5, 5], [5, 5])
    points = aggregate_weekly([a, b], planned_weeks=2)
    assert [p.planned_value for p in points] == [15.0, 30.0]


def test_horizon_extends_past_the_planned_baseline_for_a_slipped_task():
    # a task whose trace runs six weeks on a four week baseline: planned value stops
    # at week 4, but earned value and cost keep accruing into the slip weeks
    slipped = _task(
        [25, 25, 25, 25, 0, 0],
        [20, 20, 20, 20, 10, 10],
        [26, 26, 26, 26, 13, 13],
        start=1,
        end=4,
        budget=100,
    )
    points = aggregate_weekly([slipped], planned_weeks=4)
    assert len(points) == 6
    assert points[-1].planned_value == 100.0  # baseline fully accrued by week 4
    assert points[-1].earned_value == 100.0  # work finished in the slip weeks


def test_horizon_is_never_shorter_than_the_planned_baseline():
    short = _task([10, 10], [10, 10], [10, 10])
    points = aggregate_weekly([short], planned_weeks=5)
    assert len(points) == 5
    assert points[-1].planned_value == 20.0  # no extra planned value after the trace ends


def test_cost_variance_is_earned_minus_actual():
    m = _m(100, 80, 90, 100)
    assert m.cost_variance == pytest.approx(-10.0)


def test_schedule_variance_is_earned_minus_planned():
    m = _m(100, 80, 90, 100)
    assert m.schedule_variance == pytest.approx(-20.0)


def test_cpi_is_earned_over_actual():
    m = _m(100, 80, 100, 100)
    assert m.cpi == pytest.approx(0.8)


def test_spi_is_earned_over_planned():
    m = _m(100, 90, 100, 100)
    assert m.spi == pytest.approx(0.9)


def test_eac_is_budget_over_cpi():
    m = _m(100, 80, 100, 1000)
    assert m.eac == pytest.approx(1000 / 0.8)


def test_vac_is_budget_minus_eac_and_negative_when_over_budget():
    m = _m(100, 80, 100, 1000)
    assert m.vac == pytest.approx(1000 - 1250)
    assert m.vac < 0


def test_tcpi_is_remaining_work_over_remaining_budget():
    m = _m(100, 200, 250, 1000)
    assert m.tcpi == pytest.approx((1000 - 200) / (1000 - 250))


def test_cpi_is_nan_when_nothing_has_been_spent():
    m = _m(0, 0, 0, 100)
    assert math.isnan(m.cpi)


def test_spi_is_nan_before_any_baseline_has_accrued():
    m = _m(0, 0, 5, 100)
    assert math.isnan(m.spi)


def test_eac_is_nan_when_cpi_is_zero():
    # money spent but nothing earned yet: cpi is 0, so the forecast is undefined, not infinite
    m = _m(10, 0, 5, 100)
    assert m.cpi == 0.0
    assert math.isnan(m.eac)
    assert math.isnan(m.vac)


def test_tcpi_is_nan_when_actual_cost_equals_budget():
    m = _m(100, 90, 100, 100)
    assert math.isnan(m.tcpi)


@pytest.mark.parametrize(
    "pv,ev,ac",
    [
        (100, 80, 90),
        (250, 300, 275),
        (1000, 950, 1100),
        (42, 42, 42),
    ],
)
def test_the_spend_gap_decomposes_into_schedule_minus_cost(pv, ev, ac):
    # the identity the whole project rests on: AC - PV == SV - CV
    m = _m(pv, ev, ac, 2000)
    assert (ac - pv) == pytest.approx(m.schedule_variance - m.cost_variance)


def test_evaluate_rejects_a_non_positive_budget():
    with pytest.raises(ValueError, match="bac must be positive"):
        evaluate_program([_task([10], [10], [10])], bac=0, planned_weeks=1)


def test_evaluate_returns_one_metric_per_week():
    task = _task([10, 10, 10], [10, 10, 10], [10, 10, 10])
    result = evaluate_program([task], bac=30, planned_weeks=3)
    assert len(result.points) == 3


def test_final_is_the_last_weekly_metric():
    result = evaluate_program([_task([10, 10], [10, 10], [10, 10])], bac=20, planned_weeks=2)
    assert result.final.week == 2


def test_a_perfectly_executed_program_has_unit_indices():
    result = evaluate_program([_task([10, 10], [10, 10], [10, 10])], bac=20, planned_weeks=2)
    assert result.final.cpi == pytest.approx(1.0)
    assert result.final.spi == pytest.approx(1.0)
