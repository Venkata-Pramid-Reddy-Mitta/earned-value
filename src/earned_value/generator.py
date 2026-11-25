"""The seeded program generator and the fixture it writes.

The whole project turns on one modelling choice, made here and defended in
ADR-002: on a staffed delivery program, cost accrues on the calendar (the team is
paid for the weeks it is engaged) while value accrues on deliverables (you earn
budget only for work actually finished). When productivity runs below plan, the
team still costs what it costs, so actual spend keeps tracking the baseline while
earned value falls behind. That is precisely the state a burn chart cannot see and
earned value can: spend looks on-plan, schedule is already late.

The generator is deterministic. Given the seed in config.py it produces the same
sixteen tasks every run, and the committed data/program.csv is one such run, so a
reviewer reproduces every published number with no randomness of their own.

Nothing here invents a program's health. It encodes a productivity-shortfall
scenario and lets the earned-value engine report whatever that scenario produces.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import BUDGET_AT_COMPLETION, GENERATOR_SEED, PLANNED_WEEKS
from .model import Task

# (task_id, workstream, budget, planned_start_week, planned_end_week).
# Budgets sum to 2,500,000 across four workstreams. The windows overlap the way a
# real four-workstream delivery does, so several tasks are in flight at once.
_TASK_SPECS: tuple[tuple[str, str, int, int, int], ...] = (
    ("CM1-assessment", "cloud-migration", 120_000, 1, 6),
    ("CM2-landing-zone", "cloud-migration", 200_000, 4, 14),
    ("CM3-lift-shift-wave1", "cloud-migration", 260_000, 10, 24),
    ("CM4-lift-shift-wave2", "cloud-migration", 220_000, 18, 34),
    ("AM1-discovery", "app-modernization", 100_000, 3, 10),
    ("AM2-refactor-core", "app-modernization", 240_000, 8, 22),
    ("AM3-containerize", "app-modernization", 200_000, 16, 30),
    ("AM4-integration", "app-modernization", 160_000, 24, 38),
    ("DM1-schema-map", "data-migration", 110_000, 6, 14),
    ("DM2-etl-build", "data-migration", 210_000, 12, 26),
    ("DM3-bulk-load", "data-migration", 180_000, 22, 34),
    ("DM4-reconcile", "data-migration", 100_000, 30, 40),
    ("TD1-test-strategy", "testing-deployment", 70_000, 10, 18),
    ("TD2-uat-cycle1", "testing-deployment", 130_000, 20, 30),
    ("TD3-uat-cycle2", "testing-deployment", 110_000, 28, 36),
    ("TD4-cutover", "testing-deployment", 90_000, 34, 40),
)

# Per-workstream mean productivity. Below 1.0 means the workstream earns less
# budgeted value per week than it spends: the shortfall that drives the illusion.
# Cloud migration runs close to plan; the two heavy build workstreams lag.
_WORKSTREAM_PRODUCTIVITY: dict[str, float] = {
    "cloud-migration": 0.96,
    "app-modernization": 0.85,
    "data-migration": 0.87,
    "testing-deployment": 0.91,
}

_MAX_SLIP_WEEKS = 60  # a guard so a pathological draw cannot loop forever


@dataclass(frozen=True)
class Program:
    """A generated program: its tasks, its budget, its planned horizon."""

    tasks: tuple[Task, ...]
    bac: float
    planned_weeks: int


def _execute_task(
    task_id: str,
    workstream: str,
    budget: int,
    start: int,
    end: int,
    rng: np.random.Generator,
) -> Task:
    """Turn a planned task into an executed one under the shortfall model.

    productivity below 1 earns less value than is spent each planned week and
    leaves a remainder that spills into slip weeks beyond the planned end. In those
    slip weeks the baseline is exhausted (planned value is zero) but the team is
    still engaged, so cost keeps accruing: the tail that eventually pushes actual
    cost above budget.
    """

    planned_duration = end - start + 1
    weekly = budget / planned_duration
    mean_p = _WORKSTREAM_PRODUCTIVITY[workstream]
    productivity = float(np.clip(rng.normal(mean_p, 0.05), 0.72, 1.08))
    cost_factor = float(np.clip(rng.normal(1.0, 0.025), 0.92, 1.12))

    pv: dict[int, float] = defaultdict(float)
    ev: dict[int, float] = defaultdict(float)
    ac: dict[int, float] = defaultdict(float)

    earned = 0.0
    for week in range(start, end + 1):
        pv[week] = weekly
        ac[week] = weekly * cost_factor
        gain = weekly * productivity
        if earned + gain > budget:
            gain = budget - earned
        ev[week] = gain
        earned += gain

    week = end + 1
    slips = 0
    while earned < budget - 1e-6 and slips < _MAX_SLIP_WEEKS:
        gain = min(weekly, budget - earned)
        ev[week] = gain
        ac[week] = weekly * cost_factor
        earned += gain
        week += 1
        slips += 1

    last_week = max(max(pv), max(ev), max(ac))
    pv_series = tuple(pv.get(w, 0.0) for w in range(1, last_week + 1))
    ev_series = tuple(ev.get(w, 0.0) for w in range(1, last_week + 1))
    ac_series = tuple(ac.get(w, 0.0) for w in range(1, last_week + 1))

    return Task(
        task_id=task_id,
        workstream=workstream,
        budget=float(budget),
        planned_start_week=start,
        planned_end_week=end,
        planned_value=pv_series,
        earned_value=ev_series,
        actual_cost=ac_series,
    )


def generate_program(seed: int = GENERATOR_SEED) -> Program:
    """Generate the full program deterministically from a seed."""

    rng = np.random.default_rng(seed)
    tasks = tuple(
        _execute_task(task_id, workstream, budget, start, end, rng)
        for task_id, workstream, budget, start, end in _TASK_SPECS
    )
    return Program(tasks=tasks, bac=float(BUDGET_AT_COMPLETION), planned_weeks=PLANNED_WEEKS)


_CSV_FIELDS = (
    "task_id",
    "workstream",
    "budget",
    "planned_start_week",
    "planned_end_week",
    "week",
    "planned_value",
    "earned_value",
    "actual_cost",
)


def save_program(program: Program, path: Path) -> None:
    """Write the program to a long-format CSV, one row per active task-week.

    Weeks whose three increments are all zero are omitted to keep the fixture
    readable; load_program zero-fills them back, so the round trip is exact.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for task in program.tasks:
            for i in range(task.weeks):
                pv, ev, ac = (
                    task.planned_value[i],
                    task.earned_value[i],
                    task.actual_cost[i],
                )
                if pv == 0.0 and ev == 0.0 and ac == 0.0:
                    continue
                writer.writerow(
                    {
                        "task_id": task.task_id,
                        "workstream": task.workstream,
                        "budget": f"{task.budget:.2f}",
                        "planned_start_week": task.planned_start_week,
                        "planned_end_week": task.planned_end_week,
                        "week": i + 1,
                        "planned_value": f"{pv:.6f}",
                        "earned_value": f"{ev:.6f}",
                        "actual_cost": f"{ac:.6f}",
                    }
                )


def load_program(
    path: Path,
    bac: float = float(BUDGET_AT_COMPLETION),
    planned_weeks: int = PLANNED_WEEKS,
) -> Program:
    """Rebuild a Program from a fixture CSV, zero-filling omitted weeks."""

    rows_by_task: dict[str, list[dict[str, str]]] = defaultdict(list)
    order: list[str] = []
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            tid = row["task_id"]
            if tid not in rows_by_task:
                order.append(tid)
            rows_by_task[tid].append(row)

    tasks: list[Task] = []
    for tid in order:
        rows = rows_by_task[tid]
        meta = rows[0]
        last_week = max(int(r["week"]) for r in rows)
        pv = [0.0] * last_week
        ev = [0.0] * last_week
        ac = [0.0] * last_week
        for r in rows:
            idx = int(r["week"]) - 1
            pv[idx] = float(r["planned_value"])
            ev[idx] = float(r["earned_value"])
            ac[idx] = float(r["actual_cost"])
        tasks.append(
            Task(
                task_id=tid,
                workstream=meta["workstream"],
                budget=float(meta["budget"]),
                planned_start_week=int(meta["planned_start_week"]),
                planned_end_week=int(meta["planned_end_week"]),
                planned_value=tuple(pv),
                earned_value=tuple(ev),
                actual_cost=tuple(ac),
            )
        )
    return Program(tasks=tuple(tasks), bac=bac, planned_weeks=planned_weeks)
