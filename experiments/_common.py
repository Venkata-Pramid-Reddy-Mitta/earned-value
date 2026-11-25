"""Shared setup for the experiments: load the committed program once.

Every experiment reads the same committed fixture, so the numbers an experiment
prints are the numbers collect_metrics.py reads back. Nothing here regenerates the
program, because the fixture, not the generator, is the artefact a reviewer trusts.
"""

from __future__ import annotations

import json
from pathlib import Path

from earned_value.config import DEFAULT_FIXTURE
from earned_value.evm import evaluate_program
from earned_value.generator import load_program
from earned_value.model import EVMResult

EXPERIMENTS_DIR = Path(__file__).resolve().parent.parent / "docs" / "experiments"


def load_committed() -> EVMResult:
    program = load_program(DEFAULT_FIXTURE)
    return evaluate_program(program.tasks, program.bac, program.planned_weeks)


def write_json(name: str, payload: dict) -> Path:
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)
    path = EXPERIMENTS_DIR / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path
