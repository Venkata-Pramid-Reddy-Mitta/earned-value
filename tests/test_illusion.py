"""The illusion detector and the headline figures it produces.

The unit tests fix the classifier on hand-built weeks. The regression tests pin the
exact numbers the committed fixture produces, so a change to the generator or the
engine that moves a published figure turns a test red before it reaches the README.
"""

from __future__ import annotations

import math

import pytest

from earned_value.config import Tolerances
from earned_value.evm import evaluate_program, metrics_for_point
from earned_value.illusion import classify_week, summarize
from earned_value.model import EVMResult, Task, WeeklyMetrics, WeeklyPoint


def _metrics(pv, ev, ac, bac=2_500_000, week=1) -> WeeklyMetrics:
    point = WeeklyPoint(week, planned_value=pv, earned_value=ev, actual_cost=ac)
    return metrics_for_point(point, bac=bac)


def _classify(pv, ev, ac, bac=2_500_000):
    return classify_week(_metrics(pv, ev, ac, bac), bac)


def test_a_week_on_budget_and_on_schedule_is_not_an_illusion():
    v = _classify(1000, 1000, 1000)
    assert not v.is_illusion
    assert v.burn_healthy and not v.ev_late


def test_a_week_within_the_budget_band_reads_burn_healthy():
    # actual cost 1% of BAC away from plan, inside the 5% band
    v = _classify(1_000_000, 1_000_000, 1_025_000)
    assert v.burn_healthy


def test_a_week_outside_the_budget_band_does_not_read_burn_healthy():
    v = _classify(1_000_000, 1_000_000, 1_200_000)
    assert not v.burn_healthy


def test_a_low_spi_week_reads_late():
    v = _classify(1_000_000, 800_000, 1_000_000)
    assert v.ev_late


def test_the_illusion_requires_both_burn_healthy_and_ev_late():
    # spend tracks plan (burn healthy) but only 85% of scheduled value is earned
    v = _classify(1_000_000, 850_000, 1_010_000)
    assert v.burn_healthy and v.ev_late and v.is_illusion


def test_a_late_week_that_is_also_visibly_over_budget_is_not_the_illusion():
    # the burn chart would already show the overspend, so it is not concealed
    v = _classify(1_000_000, 850_000, 1_300_000)
    assert v.ev_late and not v.burn_healthy and not v.is_illusion


def test_hidden_slip_dollars_is_zero_when_the_week_is_not_an_illusion():
    v = _classify(1_000_000, 1_000_000, 1_010_000)
    assert v.hidden_slip_dollars == 0.0


def test_hidden_slip_dollars_equals_the_schedule_variance_magnitude():
    v = _classify(1_000_000, 850_000, 1_010_000)
    assert v.hidden_slip_dollars == pytest.approx(150_000)


def test_a_nan_spi_week_is_never_counted_late():
    # before any baseline accrues, spi is nan; nan < 0.95 must not read as late
    v = _classify(0, 0, 0)
    assert math.isnan(v.spi)
    assert not v.ev_late and not v.is_illusion


def test_the_budget_band_boundary_is_inclusive():
    v = _classify(1_000_000, 1_000_000, 1_125_000)  # 125000 / 2500000 == exactly 5%
    assert v.burn_gap_fraction == pytest.approx(0.05)
    assert v.burn_healthy


def test_an_invalid_tolerance_is_rejected():
    with pytest.raises(ValueError, match="strictly between 0 and 1"):
        Tolerances(spi_late=1.5)


def test_custom_tolerances_change_the_verdict():
    strict = Tolerances(spi_late=0.99)
    lenient = Tolerances(spi_late=0.80)
    m = _metrics(1_000_000, 900_000, 1_010_000)
    assert classify_week(m, 2_500_000, strict).ev_late
    assert not classify_week(m, 2_500_000, lenient).ev_late


# ---- regression tests against the committed fixture -------------------------


def test_the_program_has_fourteen_illusion_weeks(committed_result: EVMResult):
    assert summarize(committed_result).illusion_weeks == 14


def test_the_worst_concealed_slip_is_73506_dollars(committed_result: EVMResult):
    s = summarize(committed_result)
    assert round(s.worst_hidden_slip_dollars) == 73_506
    assert s.worst_hidden_slip_week == 22


def test_the_program_finishes_over_budget(committed_result: EVMResult):
    s = summarize(committed_result)
    assert round(s.forecast_overrun_dollars) == 339_975
    assert round(committed_result.final.actual_cost) == 2_839_975


def test_the_final_cpi_is_below_one(committed_result: EVMResult):
    assert round(committed_result.final.cpi, 3) == 0.880


def test_spi_recovers_to_one_at_completion_despite_finishing_late(committed_result: EVMResult):
    # the headline the author would rather not publish: SPI reads 1.000 at the end
    assert round(committed_result.final.spi, 3) == 1.000
    # yet the program only finished in week 41 on a 40 week baseline
    assert committed_result.planned_weeks == 40
    assert committed_result.final.week == 41


def test_spi_is_near_one_at_the_planned_end_while_work_remains(committed_result: EVMResult):
    w40 = next(m for m in committed_result.points if m.week == 40)
    assert round(w40.spi, 3) == 0.989  # reads almost on schedule
    assert w40.earned_value < committed_result.bac  # but the work is not finished


def test_the_spi_trough_is_far_below_the_final_spi(committed_result: EVMResult):
    defined = [m for m in committed_result.points if math.isfinite(m.spi)]
    trough = min(defined, key=lambda m: m.spi)
    assert round(trough.spi, 3) == 0.883
    assert trough.spi < committed_result.final.spi


def test_a_healthy_program_reports_no_illusion_and_no_hidden_slip():
    # an on-track program: summarize must take the empty-illusion branch cleanly
    task = Task(
        task_id="T",
        workstream="ws",
        budget=200.0,
        planned_start_week=1,
        planned_end_week=2,
        planned_value=(100.0, 100.0),
        earned_value=(100.0, 100.0),
        actual_cost=(100.0, 100.0),
    )
    result = evaluate_program([task], bac=200.0, planned_weeks=2)
    s = summarize(result)
    assert s.illusion_weeks == 0
    assert s.worst_hidden_slip_week is None
    assert s.first_illusion_week is None
    assert s.worst_hidden_slip_dollars == 0.0
