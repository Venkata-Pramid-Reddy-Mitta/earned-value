"""Experiment 1: can the burn gap be split into a cost part and a schedule part?

A burn chart shows actual_cost against planned_value. Their difference is one
number. This experiment reconstructs, for every week, that the one number is
exactly schedule_variance minus cost_variance, and reports the week where the two
parts point in opposite directions most strongly: spend near plan, schedule well
behind. That week is the clearest case of a gap a burn chart cannot read.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import load_committed, write_json


def main() -> None:
    result = load_committed()
    rows = []
    max_residual = 0.0
    for m in result.points:
        burn_gap = m.actual_cost - m.planned_value
        decomposed = m.schedule_variance - m.cost_variance
        residual = abs(burn_gap - decomposed)
        max_residual = max(max_residual, residual)
        rows.append(
            {
                "week": m.week,
                "burn_gap": round(burn_gap, 2),
                "schedule_variance": round(m.schedule_variance, 2),
                "cost_variance": round(m.cost_variance, 2),
            }
        )

    # the week with the largest schedule slip while spend stayed closest to plan
    def concealment(m):
        if m.planned_value == 0:
            return 0.0
        near_plan = 1.0 - abs(m.actual_cost - m.planned_value) / result.bac
        behind = -m.schedule_variance  # positive when behind
        return near_plan * behind

    worst = max(result.points, key=concealment)

    payload = {
        "identity": "actual_cost - planned_value == schedule_variance - cost_variance",
        "max_identity_residual_dollars": round(max_residual, 6),
        "most_concealed_week": worst.week,
        "most_concealed_schedule_variance": round(worst.schedule_variance, 2),
        "most_concealed_cost_variance": round(worst.cost_variance, 2),
        "weeks": rows,
    }
    write_json("decompose_the_gap", payload)

    print("Experiment 1: the spend gap splits into schedule and cost")
    print(f"  identity residual never exceeds ${max_residual:.6f}")
    print(
        f"  most concealed week {worst.week}: "
        f"SV ${worst.schedule_variance:,.0f}, CV ${worst.cost_variance:,.0f}"
    )


if __name__ == "__main__":
    main()
