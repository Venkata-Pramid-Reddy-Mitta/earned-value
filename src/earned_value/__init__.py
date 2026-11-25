"""earned-value: split a program's spend gap into cost and schedule effects.

Public surface used by the CLI, the experiments and the tests.
"""

from __future__ import annotations

from .config import DEFAULT_TOLERANCES, Tolerances
from .evm import aggregate_weekly, evaluate_program, metrics_for_point
from .generator import Program, generate_program, load_program, save_program
from .illusion import IllusionSummary, WeekVerdict, classify_program, classify_week, summarize
from .model import EVMResult, Task, WeeklyMetrics, WeeklyPoint

__all__ = [
    "DEFAULT_TOLERANCES",
    "Tolerances",
    "aggregate_weekly",
    "evaluate_program",
    "metrics_for_point",
    "Program",
    "generate_program",
    "load_program",
    "save_program",
    "IllusionSummary",
    "WeekVerdict",
    "classify_program",
    "classify_week",
    "summarize",
    "EVMResult",
    "Task",
    "WeeklyMetrics",
    "WeeklyPoint",
]

__version__ = "0.1.0"
