"""Central configuration.

This file exists so the thresholds that decide "healthy" are data, not magic
numbers scattered through the engine. An auditor changes one tolerance here and
re-runs; nothing in evm.py or illusion.py hardcodes a limit. The defaults encode
the one claim this project interrogates: a program manager reporting spend
"within 5% of budget" (the band below) and calling it healthy.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Repository-root-relative path to the committed, seeded fixture. Resolved from
# this file so the CLI and the experiments find it regardless of the caller's
# working directory.
PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent.parent
DEFAULT_FIXTURE = REPO_ROOT / "data" / "program.csv"


@dataclass(frozen=True)
class Tolerances:
    """The thresholds that separate "healthy" from "late" or "over".

    budget_band is the cost-only read a burn chart gives: cumulative actual cost
    within this fraction of the planned baseline, expressed against the total
    budget (BAC). It is the "spend within 5% of budget" statement made precise.

    spi_late and cpi_over are the earned-value reads the burn chart cannot give.
    A week is part of the illusion when the burn read is inside budget_band while
    SPI has already crossed spi_late.
    """

    budget_band: float = 0.05
    spi_late: float = 0.95
    cpi_over: float = 0.95

    def __post_init__(self) -> None:
        for name, value in (
            ("budget_band", self.budget_band),
            ("spi_late", self.spi_late),
            ("cpi_over", self.cpi_over),
        ):
            if not 0.0 < value < 1.0:
                raise ValueError(f"{name} must be strictly between 0 and 1, got {value}")


DEFAULT_TOLERANCES = Tolerances()

# The generator's contract: a 2.5M program over a 40 week planned baseline, four
# workstreams. Kept here so a reader sees the shape without opening generator.py.
BUDGET_AT_COMPLETION = 2_500_000
PLANNED_WEEKS = 40
GENERATOR_SEED = 20260224
