"""Command line entry point with exit codes that mean something.

Three outcomes are kept distinct, because a status gate that cannot tell "I ran
and the answer is no" from "I could not run" is not trustworthy in CI:

    0  the tool ran and the week is healthy on both reads
    1  the tool ran and the week is flagged (behind schedule or over cost)
    2  the tool could not answer (bad arguments, missing or malformed fixture)

argparse already exits 2 on an argument error, so the usage class is consistent.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Sequence
from pathlib import Path

from .config import DEFAULT_FIXTURE, DEFAULT_TOLERANCES, GENERATOR_SEED
from .evm import evaluate_program
from .generator import generate_program, load_program, save_program
from .illusion import classify_program, summarize
from .model import EVMResult

EXIT_OK = 0
EXIT_FLAGGED = 1
EXIT_USAGE = 2


def _fmt(value: float) -> str:
    return "n/a" if not math.isfinite(value) else f"{value:,.0f}"


def _fmt_idx(value: float) -> str:
    return "n/a" if not math.isfinite(value) else f"{value:.3f}"


def _load(fixture: Path) -> EVMResult:
    program = load_program(fixture)
    return evaluate_program(program.tasks, program.bac, program.planned_weeks)


def _cmd_report(args: argparse.Namespace) -> int:
    result = _load(args.fixture)
    rows = result.points
    if args.week is not None:
        rows = [m for m in rows if m.week == args.week]
        if not rows:
            print(f"week {args.week} is outside the program horizon", file=sys.stderr)
            return EXIT_USAGE
    if args.json:
        payload = [
            {
                "week": m.week,
                "pv": m.planned_value,
                "ev": m.earned_value,
                "ac": m.actual_cost,
                "cv": m.cost_variance,
                "sv": m.schedule_variance,
                "cpi": m.cpi,
                "spi": m.spi,
                "eac": m.eac,
                "vac": m.vac,
                "tcpi": m.tcpi,
            }
            for m in rows
        ]
        print(json.dumps(payload, indent=2))
        return EXIT_OK

    print(f"{'wk':>3}  {'PV':>11} {'EV':>11} {'AC':>11}  {'SPI':>6} {'CPI':>6}  {'EAC':>11}")
    for m in rows:
        print(
            f"{m.week:>3}  {_fmt(m.planned_value):>11} {_fmt(m.earned_value):>11} "
            f"{_fmt(m.actual_cost):>11}  {_fmt_idx(m.spi):>6} {_fmt_idx(m.cpi):>6}  "
            f"{_fmt(m.eac):>11}"
        )
    return EXIT_OK


def _cmd_gate(args: argparse.Namespace) -> int:
    result = _load(args.fixture)
    week = args.week if args.week is not None else result.final.week
    match = [m for m in result.points if m.week == week]
    if not match:
        print(f"week {week} is outside the program horizon", file=sys.stderr)
        return EXIT_USAGE
    m = match[0]
    tol = DEFAULT_TOLERANCES
    late = math.isfinite(m.spi) and m.spi < tol.spi_late
    over = math.isfinite(m.cpi) and m.cpi < tol.cpi_over
    burn_gap = abs(m.actual_cost - m.planned_value) / result.bac

    print(
        f"week {week}: SPI={_fmt_idx(m.spi)} CPI={_fmt_idx(m.cpi)} "
        f"burn-gap={burn_gap * 100:.2f}% of BAC"
    )
    if late or over:
        reasons = []
        if late:
            reasons.append(f"behind schedule (SPI<{tol.spi_late})")
        if over:
            reasons.append(f"over cost (CPI<{tol.cpi_over})")
        healthy_burn = burn_gap <= tol.budget_band
        if healthy_burn:
            print(
                f"FLAGGED: {', '.join(reasons)}. Note: spend is within "
                f"{tol.budget_band * 100:.0f}% of baseline, so a burn chart would read healthy."
            )
        else:
            print(f"FLAGGED: {', '.join(reasons)}.")
        return EXIT_FLAGGED
    print("HEALTHY on both reads.")
    return EXIT_OK


def _cmd_illusions(args: argparse.Namespace) -> int:
    result = _load(args.fixture)
    verdicts = classify_program(result)
    summary = summarize(result)
    print("Weeks a burn chart read healthy (spend within band) while earned value read late:")
    print(f"{'wk':>3}  {'SPI':>6} {'burn-gap':>9}  {'hidden slip $':>14}")
    for v in verdicts:
        if v.is_illusion:
            print(
                f"{v.week:>3}  {_fmt_idx(v.spi):>6} {v.burn_gap_fraction * 100:>7.2f}%  "
                f"{_fmt(v.hidden_slip_dollars):>14}"
            )
    print()
    print(f"illusion weeks: {summary.illusion_weeks}")
    if summary.worst_hidden_slip_week is not None:
        print(
            f"worst concealed slip: ${summary.worst_hidden_slip_dollars:,.0f} "
            f"at week {summary.worst_hidden_slip_week}"
        )
    print(f"final SPI {_fmt_idx(summary.final_spi)}  final CPI {_fmt_idx(summary.final_cpi)}")
    print(f"forecast overrun at completion: ${summary.forecast_overrun_dollars:,.0f}")
    return EXIT_OK


def _cmd_generate(args: argparse.Namespace) -> int:
    program = generate_program(seed=args.seed)
    save_program(program, args.out)
    print(f"wrote {len(program.tasks)} tasks to {args.out} (seed {args.seed})")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="earned-value",
        description="Split a program's spend gap into cost and schedule effects.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_report = sub.add_parser("report", help="print the weekly earned-value table")
    p_report.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    p_report.add_argument("--week", type=int, default=None)
    p_report.add_argument("--json", action="store_true")
    p_report.set_defaults(func=_cmd_report)

    p_gate = sub.add_parser("gate", help="exit 1 if a week is behind or over, 0 if healthy")
    p_gate.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    p_gate.add_argument("--week", type=int, default=None)
    p_gate.set_defaults(func=_cmd_gate)

    p_ill = sub.add_parser("illusions", help="list weeks the burn read healthy while EV read late")
    p_ill.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    p_ill.set_defaults(func=_cmd_illusions)

    p_gen = sub.add_parser("generate", help="regenerate the seeded fixture")
    p_gen.add_argument("--out", type=Path, default=DEFAULT_FIXTURE)
    p_gen.add_argument("--seed", type=int, default=GENERATOR_SEED)
    p_gen.set_defaults(func=_cmd_generate)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except FileNotFoundError as exc:
        print(f"fixture not found: {exc.filename}", file=sys.stderr)
        return EXIT_USAGE
    except (ValueError, KeyError) as exc:
        print(f"could not read program: {exc}", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
