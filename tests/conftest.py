"""Shared fixtures: the committed program, evaluated once."""

from __future__ import annotations

import pytest

from earned_value.config import DEFAULT_FIXTURE
from earned_value.evm import evaluate_program
from earned_value.generator import load_program
from earned_value.model import EVMResult


@pytest.fixture(scope="session")
def committed_result() -> EVMResult:
    program = load_program(DEFAULT_FIXTURE)
    return evaluate_program(program.tasks, program.bac, program.planned_weeks)
