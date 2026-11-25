"""Model construction and boundary validation.

The model refuses a malformed task at construction rather than letting a bad trace
produce a quietly wrong curve downstream, so these tests pin the refusals.
"""

from __future__ import annotations

import pytest

from earned_value.model import Task, WeeklyMetrics, WeeklyPoint


def _good_task(**over) -> Task:
    base = dict(
        task_id="T1",
        workstream="ws",
        budget=100.0,
        planned_start_week=1,
        planned_end_week=4,
        planned_value=(25.0, 25.0, 25.0, 25.0),
        earned_value=(20.0, 20.0, 20.0, 20.0),
        actual_cost=(26.0, 26.0, 26.0, 26.0),
    )
    base.update(over)
    return Task(**base)


def test_a_well_formed_task_is_accepted():
    task = _good_task()
    assert task.task_id == "T1"


def test_task_weeks_reports_the_trace_length():
    assert _good_task().weeks == 4


def test_a_zero_budget_task_is_rejected():
    with pytest.raises(ValueError, match="budget must be positive"):
        _good_task(budget=0.0)


def test_a_negative_budget_task_is_rejected():
    with pytest.raises(ValueError, match="budget must be positive"):
        _good_task(budget=-10.0)


def test_a_start_week_below_one_is_rejected():
    with pytest.raises(ValueError, match="planned_start_week must be >= 1"):
        _good_task(planned_start_week=0)


def test_an_end_week_before_the_start_week_is_rejected():
    with pytest.raises(ValueError, match="planned_end_week before planned_start_week"):
        _good_task(planned_start_week=5, planned_end_week=4)


def test_mismatched_series_lengths_are_rejected():
    with pytest.raises(ValueError, match="series lengths differ"):
        _good_task(planned_value=(25.0, 25.0, 25.0))


def test_a_negative_planned_value_increment_is_rejected():
    with pytest.raises(ValueError, match="planned_value has a negative"):
        _good_task(planned_value=(25.0, -1.0, 25.0, 25.0))


def test_a_negative_earned_value_increment_is_rejected():
    with pytest.raises(ValueError, match="earned_value has a negative"):
        _good_task(earned_value=(20.0, 20.0, -5.0, 20.0))


def test_a_negative_actual_cost_increment_is_rejected():
    with pytest.raises(ValueError, match="actual_cost has a negative"):
        _good_task(actual_cost=(26.0, 26.0, 26.0, -1.0))


def test_a_task_may_start_after_week_one():
    task = _good_task(planned_start_week=3, planned_end_week=6)
    assert task.planned_start_week == 3


def test_weekly_point_is_a_transparent_record():
    point = WeeklyPoint(week=2, planned_value=50.0, earned_value=40.0, actual_cost=52.0)
    assert point.week == 2
    assert (point.planned_value, point.earned_value, point.actual_cost) == (50.0, 40.0, 52.0)


def test_weekly_metrics_carries_every_derived_field():
    m = WeeklyMetrics(
        week=1,
        planned_value=1.0,
        earned_value=1.0,
        actual_cost=1.0,
        cost_variance=0.0,
        schedule_variance=0.0,
        cpi=1.0,
        spi=1.0,
        eac=1.0,
        vac=0.0,
        tcpi=1.0,
    )
    assert m.week == 1 and m.cpi == 1.0 and m.vac == 0.0
