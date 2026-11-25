"""Generate the evidence: the burn-vs-earned-value chart and a replay manifest.

The chart is the whole argument in one picture. The left panel is the burn chart a
status report shows: actual cost against the planned baseline, staying inside the
5% band for most of the program, which reads healthy. The right panel adds the one
line a burn chart never plots, earned value, and shades the weeks where spend was
inside the band while schedule performance was already late. Both panels are drawn
from the committed fixture, so the picture cannot drift from the numbers.

matplotlib is a build-time dependency (the viz extra), never imported by the
metrics path, so the no-extras CI job proves the tool runs without it.

The manifest records the five demo commands actually run, with their real exit
codes and captured wall time: a replay, not a staged recording.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = REPO_ROOT / "docs" / "evidence"

sys.path.insert(0, str(REPO_ROOT / "src"))

from earned_value.config import DEFAULT_TOLERANCES  # noqa: E402
from earned_value.evm import evaluate_program  # noqa: E402
from earned_value.generator import load_program  # noqa: E402
from earned_value.illusion import classify_program  # noqa: E402


def _draw_chart() -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    program = load_program(REPO_ROOT / "data" / "program.csv")
    result = evaluate_program(program.tasks, program.bac, program.planned_weeks)
    verdicts = classify_program(result)
    bac = result.bac

    weeks = [m.week for m in result.points]
    pv = [m.planned_value for m in result.points]
    ev = [m.earned_value for m in result.points]
    ac = [m.actual_cost for m in result.points]
    illusion_weeks = [v.week for v in verdicts if v.is_illusion]

    fig, (left, right) = plt.subplots(1, 2, figsize=(12, 5), sharex=True, sharey=True)

    # Left: the burn chart. Planned vs actual only, with the 5% band around plan.
    band = DEFAULT_TOLERANCES.budget_band * bac
    left.plot(weeks, pv, color="#2563eb", label="Planned value (baseline)")
    left.plot(weeks, ac, color="#dc2626", label="Actual cost")
    left.fill_between(weeks, [p - band for p in pv], [p + band for p in pv],
                      color="#2563eb", alpha=0.12, label="+/- 5% of BAC band")
    left.set_title("What a burn chart shows: spend near plan")
    left.set_xlabel("Week")
    left.set_ylabel("Cumulative dollars")
    left.legend(loc="upper left", fontsize=8)
    left.grid(True, alpha=0.3)

    # Right: add earned value, shade the concealed weeks.
    right.plot(weeks, pv, color="#2563eb", label="Planned value")
    right.plot(weeks, ac, color="#dc2626", label="Actual cost")
    right.plot(weeks, ev, color="#059669", linewidth=2.5, label="Earned value")
    for w in illusion_weeks:
        right.axvspan(w - 0.5, w + 0.5, color="#f59e0b", alpha=0.18)
    right.set_title("What earned value adds: the schedule was already late")
    right.set_xlabel("Week")
    handles, labels = right.get_legend_handles_labels()
    handles.append(Patch(facecolor="#f59e0b", alpha=0.3))
    labels.append("illusion week (burn healthy, SPI < 0.95)")
    right.legend(handles, labels, loc="upper left", fontsize=8)
    right.grid(True, alpha=0.3)

    fig.suptitle(
        "earned-value: the same $2,500,000 program, read two ways",
        fontsize=14,
        fontweight="bold",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE / "burn-vs-earned-value.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out


_DEMO_COMMANDS = [
    [sys.executable, "-m", "earned_value.cli", "report", "--week", "22"],
    [sys.executable, "-m", "earned_value.cli", "gate", "--week", "5"],
    [sys.executable, "-m", "earned_value.cli", "gate", "--week", "40"],
    [sys.executable, "-m", "earned_value.cli", "illusions"],
    [sys.executable, "experiments/spi_blindness.py"],
]


def _record_manifest() -> Path:
    entries = []
    # warm the import so the first timing is not inflated by interpreter start
    subprocess.run([sys.executable, "-c", "import earned_value"], cwd=REPO_ROOT, check=False)
    for command in _DEMO_COMMANDS:
        start = time.perf_counter()
        proc = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True)
        duration = time.perf_counter() - start
        display = " ".join(c.replace(sys.executable, "python") for c in command)
        entries.append(
            {
                "command": display,
                "exit_code": proc.returncode,
                "duration_s": round(duration, 3),
                "stdout_lines": proc.stdout.count("\n"),
            }
        )
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE / "manifest.json"
    out.write_text(json.dumps({"commands": entries}, indent=2) + "\n")
    return out


def main() -> None:
    chart = _draw_chart()
    print(f"wrote {chart.relative_to(REPO_ROOT)} ({chart.stat().st_size} bytes)")
    manifest = _record_manifest()
    print(f"wrote {manifest.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
