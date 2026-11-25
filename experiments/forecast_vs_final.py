"""Experiment 3: how early did the cost forecast see the overrun the burn hid?

The independent estimate at completion is EAC = BAC / CPI. Because CPI is roughly
flat from the first weeks, EAC forecasts the final actual cost long before the burn
chart's gap grows large enough to notice. This experiment reports the final overrun
and the earliest week EAC was already within 5% of that final number.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import load_committed, write_json


def main() -> None:
    result = load_committed()
    bac = result.bac
    final_ac = result.final.actual_cost
    final_overrun = final_ac - bac

    early_week = None
    for m in result.points:
        if math.isfinite(m.eac) and abs(m.eac - final_ac) <= 0.05 * bac:
            early_week = m.week
            break

    payload = {
        "bac": round(bac, 2),
        "final_actual_cost": round(final_ac, 2),
        "final_overrun_dollars": round(final_overrun, 2),
        "final_overrun_pct": round(final_overrun / bac * 100, 1),
        "final_cpi": round(result.final.cpi, 4),
        "eac_within_5pct_of_final_by_week": early_week,
        "planned_weeks": result.planned_weeks,
    }
    write_json("forecast_vs_final", payload)

    print("Experiment 3: the cost forecast saw the overrun early")
    print(f"  final overrun ${final_overrun:,.0f} ({payload['final_overrun_pct']}% of BAC)")
    print(f"  EAC was within 5% of the final cost by week {early_week}")


if __name__ == "__main__":
    main()
