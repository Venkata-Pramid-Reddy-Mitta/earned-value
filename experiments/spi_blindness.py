"""Experiment 4: the tool's own blind spot, published rather than hidden.

SPI is earned value over planned value. As a program finishes, both converge on
BAC, so SPI returns to 1.0 no matter how late the finish. This experiment measures
that: the SPI trough, the near-1.0 reading at the planned end while work remained,
and the exact 1.0 at completion in a week beyond the baseline. CPI shows no such
recovery, which is why the cost read stays trustworthy to the end and the schedule
read does not.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import load_committed, write_json


def main() -> None:
    result = load_committed()
    defined = [m for m in result.points if math.isfinite(m.spi)]
    trough = min(defined, key=lambda m: m.spi)
    planned_end = next(m for m in result.points if m.week == result.planned_weeks)
    final = result.final

    payload = {
        "spi_trough": round(trough.spi, 4),
        "spi_trough_week": trough.week,
        "spi_at_planned_end": round(planned_end.spi, 4),
        "earned_fraction_at_planned_end": round(planned_end.earned_value / result.bac, 4),
        "spi_at_completion": round(final.spi, 4),
        "completion_week": final.week,
        "planned_weeks": result.planned_weeks,
        "cpi_trough": round(min(m.cpi for m in defined), 4),
        "cpi_at_completion": round(final.cpi, 4),
    }
    write_json("spi_blindness", payload)

    print("Experiment 4: SPI goes blind near completion, CPI does not")
    print(f"  SPI trough {trough.spi:.3f} at week {trough.week}")
    print(
        f"  SPI recovers to {planned_end.spi:.3f} at the planned end "
        f"(week {result.planned_weeks}) with work still unfinished"
    )
    print(f"  SPI reads {final.spi:.3f} at completion in week {final.week}")
    print(f"  CPI stays at {final.cpi:.3f}: the cost read never recovered")


if __name__ == "__main__":
    main()
