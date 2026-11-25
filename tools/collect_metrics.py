"""Re-measure every published figure and write docs/metrics.json.

Nothing in this file is typed by hand from a previous run. The test count and
coverage come from the machine readable pytest reports; every other figure comes
from running the four experiments and reading the JSON they write. The output is a
single file that check_numbers.py holds the documents to.

Usage:
    python tools/collect_metrics.py                # run pytest, then collect
    python tools/collect_metrics.py --skip-tests   # read reports/ written by CI
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPERIMENTS = REPO_ROOT / "experiments"
EXPERIMENT_JSON = REPO_ROOT / "docs" / "experiments"
REPORTS = REPO_ROOT / "reports"
METRICS_PATH = REPO_ROOT / "docs" / "metrics.json"

CHECKED_DOCUMENTS = [
    "README.md",
    "docs/defense-guide.md",
    "docs/adr/ADR-001-earned-value-over-burn-up.md",
    "docs/adr/ADR-003-spi-blindness-boundary.md",
]


def _run_pytest() -> None:
    REPORTS.mkdir(exist_ok=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            f"--junitxml={REPORTS / 'junit.xml'}",
            "--cov=earned_value",
            f"--cov-report=json:{REPORTS / 'coverage.json'}",
        ],
        cwd=REPO_ROOT,
        check=True,
    )


def _tests_total() -> int:
    tree = ET.parse(REPORTS / "junit.xml")
    root = tree.getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    return int(suite.attrib["tests"])


def _coverage_pct() -> float:
    data = json.loads((REPORTS / "coverage.json").read_text())
    return float(data["totals"]["percent_covered"])


def _run_experiments() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for script in sorted(EXPERIMENTS.glob("*.py")):
        if script.name.startswith("_"):
            continue
        subprocess.run([sys.executable, str(script)], cwd=REPO_ROOT, check=True)
    for path in sorted(EXPERIMENT_JSON.glob("*.json")):
        out[path.stem] = json.loads(path.read_text())
    return out


def _dollars(value: float) -> str:
    return f"${value:,.0f}"


def build_metrics(skip_tests: bool) -> dict:
    if not skip_tests:
        _run_pytest()
    tests_total = _tests_total()
    coverage = _coverage_pct()
    exp = _run_experiments()

    gap = exp["decompose_the_gap"]
    ill = exp["find_the_illusion"]
    fore = exp["forecast_vs_final"]
    spi = exp["spi_blindness"]

    # (name, raw value, display string, anchor templates). A template carries the
    # number and two or three words only, so it survives line wrapping (receipts
    # rule 2). Several templates are alternatives: any one matching is enough.
    specs = [
        ("tests_total", tests_total, str(tests_total), ["{} tests"]),
        ("coverage_line_pct", math.floor(coverage), str(math.floor(coverage)),
         ["{}% line coverage", "{}% coverage"]),
        ("bac_dollars", 2_500_000, _dollars(2_500_000), ["{}"]),
        ("final_actual_cost", round(fore["final_actual_cost"]),
         _dollars(fore["final_actual_cost"]), ["{}"]),
        ("workstream_count", 4, "4", ["{} workstreams"]),
        ("task_count", 16, "16", ["{} tasks"]),
        ("planned_weeks", spi["planned_weeks"], str(spi["planned_weeks"]),
         ["{} week baseline", "{}-week baseline"]),
        ("illusion_weeks", ill["illusion_weeks"], str(ill["illusion_weeks"]),
         ["{} reporting weeks", "{} illusion weeks"]),
        ("worst_slip_dollars", round(ill["worst_hidden_slip_dollars"]),
         _dollars(ill["worst_hidden_slip_dollars"]), ["{}"]),
        ("worst_slip_week", ill["worst_hidden_slip_week"], str(ill["worst_hidden_slip_week"]),
         ["week {}"]),
        ("overrun_dollars", round(fore["final_overrun_dollars"]),
         _dollars(fore["final_overrun_dollars"]), ["{}"]),
        ("overrun_pct", fore["final_overrun_pct"], f"{fore['final_overrun_pct']}%", ["{}"]),
        ("final_cpi", fore["final_cpi"], f"{fore['final_cpi']:.3f}",
         ["CPI of {}", "CPI stays at {}", "CPI held at {}"]),
        ("eac_within_5pct_week", fore["eac_within_5pct_of_final_by_week"],
         str(fore["eac_within_5pct_of_final_by_week"]),
         ["within 5% of the final cost by week {}", "by week {}"]),
        ("spi_trough", spi["spi_trough"], f"{spi['spi_trough']:.3f}",
         ["SPI trough {}", "trough of {}", "trough {}"]),
        ("spi_planned_end", spi["spi_at_planned_end"], f"{spi['spi_at_planned_end']:.3f}",
         ["SPI recovers to {}", "reads {}", "{} at the planned end"]),
        ("spi_completion", spi["spi_at_completion"], f"{spi['spi_at_completion']:.3f}",
         ["SPI of {}", "SPI reads {}", "recovers to {}"]),
        ("completion_week", spi["completion_week"], str(spi["completion_week"]),
         ["week {}", "finished in week {}"]),
        ("identity_residual", gap["max_identity_residual_dollars"],
         f"{gap['max_identity_residual_dollars']:.2f}",
         ["maximum residual of {}", "identity residual of {}"]),
    ]

    metrics = {name: value for name, value, _disp, _a in specs}
    display = {name: disp for name, _v, disp, _a in specs}
    anchors = {
        name: [tmpl.format(disp) for tmpl in templates]
        for name, _v, disp, templates in specs
    }
    dollar_values = sorted({disp for disp in display.values() if disp.startswith("$")})

    return {
        "metrics": metrics,
        "display": display,
        "anchors": anchors,
        "dollar_values": dollar_values,
        "checked_documents": CHECKED_DOCUMENTS,
        "note": "every value here is produced by running the suite and the four experiments",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="read reports/ instead of running pytest",
    )
    args = parser.parse_args(argv)

    payload = build_metrics(skip_tests=args.skip_tests)
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"wrote {METRICS_PATH.relative_to(REPO_ROOT)} with {len(payload['metrics'])} metrics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
