"""The command line surface and its exit codes.

The exit codes are a contract (0 healthy, 1 flagged, 2 could not answer), so each
is pinned. Output is captured rather than asserted word for word, except where a
specific line carries the project's point (the burn-chart note on a concealed week).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from earned_value.cli import EXIT_FLAGGED, EXIT_OK, EXIT_USAGE, main


def test_report_prints_a_table_and_exits_zero(capsys):
    assert main(["report"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "PV" in out and "SPI" in out


def test_report_can_emit_json(capsys):
    assert main(["report", "--json", "--week", "10"]) == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["week"] == 10
    assert "spi" in payload[0]


def test_report_json_without_a_week_covers_the_whole_horizon(capsys):
    assert main(["report", "--json"]) == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == 41
    assert payload[0]["week"] == 1


def test_report_for_a_week_outside_the_horizon_is_a_usage_error(capsys):
    assert main(["report", "--week", "500"]) == EXIT_USAGE
    assert "outside the program horizon" in capsys.readouterr().err


def test_gate_on_a_flagged_week_exits_one(capsys):
    assert main(["gate", "--week", "5"]) == EXIT_FLAGGED
    assert "FLAGGED" in capsys.readouterr().out


def test_gate_on_a_concealed_week_names_the_burn_chart(capsys):
    main(["gate", "--week", "5"])
    out = capsys.readouterr().out
    assert "burn chart would read healthy" in out


def test_gate_on_a_healthy_week_exits_zero(tmp_path: Path, capsys):
    # build a tiny on-track fixture so a healthy gate is exercised
    fixture = tmp_path / "ok.csv"
    fixture.write_text(
        "task_id,workstream,budget,planned_start_week,planned_end_week,week,"
        "planned_value,earned_value,actual_cost\n"
        "T,ws,100.000000,1,2,1,50.000000,50.000000,50.000000\n"
        "T,ws,100.000000,1,2,2,50.000000,50.000000,50.000000\n"
    )
    assert main(["gate", "--fixture", str(fixture)]) == EXIT_OK
    assert "HEALTHY" in capsys.readouterr().out


def test_gate_on_a_visibly_overspent_week_flags_without_the_burn_note(capsys):
    # week 40 is 12% of BAC over plan, so the overspend is not concealed
    assert main(["gate", "--week", "40"]) == EXIT_FLAGGED
    out = capsys.readouterr().out
    assert "FLAGGED" in out
    assert "burn chart would read healthy" not in out


def test_gate_for_a_week_outside_the_horizon_is_a_usage_error(capsys):
    assert main(["gate", "--week", "500"]) == EXIT_USAGE
    assert "outside the program horizon" in capsys.readouterr().err


def test_gate_on_a_missing_fixture_is_a_usage_error(capsys):
    assert main(["gate", "--fixture", "/no/such/file.csv"]) == EXIT_USAGE
    assert "fixture not found" in capsys.readouterr().err


def test_illusions_lists_weeks_and_a_summary(capsys):
    assert main(["illusions"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "illusion weeks: 14" in out
    assert "worst concealed slip" in out


def test_generate_writes_a_fixture(tmp_path: Path, capsys):
    out = tmp_path / "gen.csv"
    assert main(["generate", "--out", str(out), "--seed", "7"]) == EXIT_OK
    assert out.exists()
    assert "wrote 16 tasks" in capsys.readouterr().out


def test_a_malformed_fixture_is_a_usage_error(tmp_path: Path, capsys):
    bad = tmp_path / "bad.csv"
    bad.write_text(
        "task_id,workstream,budget,planned_start_week,planned_end_week,week,"
        "planned_value,earned_value,actual_cost\n"
        "T,ws,-5.0,1,2,1,50.0,50.0,50.0\n"  # negative budget is refused by the model
    )
    assert main(["gate", "--fixture", str(bad)]) == EXIT_USAGE
    assert "could not read program" in capsys.readouterr().err


def test_no_subcommand_is_a_usage_error():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == EXIT_USAGE
