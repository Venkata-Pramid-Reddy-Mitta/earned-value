"""The seeded generator and the fixture round trip.

The generator must be deterministic (a reviewer reproduces every number) and the
CSV round trip must be faithful. test_the_csv_round_trip_needs_a_cent_tolerance
pins the real bug this build hit: money written to six decimal places does not sum
back to an exact dollar figure, so an equality assertion on the reloaded total is
wrong and a tolerance is right.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from earned_value.config import BUDGET_AT_COMPLETION, GENERATOR_SEED
from earned_value.generator import generate_program, load_program, save_program


def test_the_generator_builds_sixteen_tasks():
    assert len(generate_program().tasks) == 16


def test_the_generator_is_deterministic_for_a_fixed_seed():
    a = generate_program(seed=GENERATOR_SEED)
    b = generate_program(seed=GENERATOR_SEED)
    assert [t.earned_value for t in a.tasks] == [t.earned_value for t in b.tasks]
    assert [t.actual_cost for t in a.tasks] == [t.actual_cost for t in b.tasks]


def test_a_different_seed_changes_the_execution():
    a = generate_program(seed=1)
    b = generate_program(seed=2)
    assert [t.actual_cost for t in a.tasks] != [t.actual_cost for t in b.tasks]


def test_task_budgets_sum_to_the_budget_at_completion():
    total = sum(t.budget for t in generate_program().tasks)
    assert total == pytest.approx(BUDGET_AT_COMPLETION)


def test_every_task_earns_its_whole_budget():
    for task in generate_program().tasks:
        assert sum(task.earned_value) == pytest.approx(task.budget, abs=1e-6)


def test_every_task_plans_its_whole_budget():
    for task in generate_program().tasks:
        assert sum(task.planned_value) == pytest.approx(task.budget, abs=1e-6)


def test_a_lagging_task_spends_more_than_its_budget():
    # at least one task overruns cost: the productivity shortfall tail
    overruns = [t for t in generate_program().tasks if sum(t.actual_cost) > t.budget + 1]
    assert overruns


def test_planned_value_only_accrues_inside_the_planned_window():
    for task in generate_program().tasks:
        before = task.planned_value[: task.planned_start_week - 1]
        after = task.planned_value[task.planned_end_week:]
        assert sum(before) == 0.0
        assert sum(after) == 0.0


def test_the_four_workstreams_are_all_present():
    names = {t.workstream for t in generate_program().tasks}
    assert names == {
        "cloud-migration",
        "app-modernization",
        "data-migration",
        "testing-deployment",
    }


def test_save_then_load_preserves_task_count(tmp_path: Path):
    prog = generate_program()
    path = tmp_path / "program.csv"
    save_program(prog, path)
    assert len(load_program(path).tasks) == len(prog.tasks)


def test_save_then_load_preserves_the_planned_window(tmp_path: Path):
    prog = generate_program()
    path = tmp_path / "program.csv"
    save_program(prog, path)
    reloaded = {t.task_id: t for t in load_program(path).tasks}
    for task in prog.tasks:
        r = reloaded[task.task_id]
        assert r.planned_start_week == task.planned_start_week
        assert r.planned_end_week == task.planned_end_week


def test_the_csv_round_trip_needs_a_cent_tolerance(tmp_path: Path):
    # The build hit this: sum(earned_value) over the reloaded fixture is NOT exactly
    # BUDGET_AT_COMPLETION, because each weekly dollar amount is written to six
    # decimal places and the rounding does not cancel. The drift is under a cent,
    # so the fixture is trustworthy, but an exact equality check is a false red.
    prog = generate_program()
    path = tmp_path / "program.csv"
    save_program(prog, path)
    reloaded = load_program(path)
    total = sum(sum(t.earned_value) for t in reloaded.tasks)

    assert total != BUDGET_AT_COMPLETION  # the exact check that was wrong
    assert total == pytest.approx(BUDGET_AT_COMPLETION, abs=0.01)  # the tolerance that is right


def test_save_omits_all_zero_weeks(tmp_path: Path):
    prog = generate_program()
    path = tmp_path / "program.csv"
    save_program(prog, path)
    text = path.read_text().splitlines()
    # a task starting at week 3 must not write rows for weeks 1 and 2
    cm2 = [ln for ln in text if ln.startswith("CM2-landing-zone")]
    first_week = min(int(ln.split(",")[5]) for ln in cm2)
    assert first_week == 4


def test_load_rejects_a_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_program(tmp_path / "does-not-exist.csv")
