"""Experiment 2: how many weeks did the burn read healthy while EV read late?

This is the headline. It counts the reporting weeks where cumulative spend stayed
within the budget band (a burn chart reads on-plan) at the same moment SPI was
already below the late threshold, and reports the worst single week by the dollar
value of the scheduled work that had not been earned.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import load_committed, write_json

from earned_value.illusion import classify_program, summarize


def main() -> None:
    result = load_committed()
    verdicts = classify_program(result)
    summary = summarize(result)

    illusion_weeks = [
        {
            "week": v.week,
            "spi": round(v.spi, 4),
            "burn_gap_pct_of_bac": round(v.burn_gap_fraction * 100, 2),
            "hidden_slip_dollars": round(v.hidden_slip_dollars, 2),
        }
        for v in verdicts
        if v.is_illusion
    ]

    payload = {
        "budget_band_pct": 5,
        "spi_late_threshold": 0.95,
        "illusion_weeks": summary.illusion_weeks,
        "first_illusion_week": summary.first_illusion_week,
        "worst_hidden_slip_dollars": round(summary.worst_hidden_slip_dollars, 2),
        "worst_hidden_slip_week": summary.worst_hidden_slip_week,
        "weeks": illusion_weeks,
    }
    write_json("find_the_illusion", payload)

    print("Experiment 2: weeks the burn read healthy while earned value read late")
    print(f"  {summary.illusion_weeks} reporting weeks were an illusion")
    print(
        f"  worst concealed slip ${summary.worst_hidden_slip_dollars:,.0f} "
        f"at week {summary.worst_hidden_slip_week}"
    )


if __name__ == "__main__":
    main()
