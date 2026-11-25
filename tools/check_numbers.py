"""Fail the build when a document quotes a figure the code no longer produces.

Two checks, matching references/receipts.md:

Forward: every metric in docs/metrics.json must appear, with its current value, in
at least one checked document, using one of its anchor phrases. If a metric moves
and a document was not updated, the old phrase no longer matches and the build
fails. Whitespace is normalised first so an anchor that straddles a line break in
wrapped markdown still matches (receipts rule 2).

Reverse: every dollar figure written in the checked documents must be one of the
figures metrics.json actually produces. A dollar amount that matches no metric is a
number nothing re-measures, so it fails the build. Dollar tokens inside fenced code
blocks and inline code spans are ignored, because an example invocation is allowed
to contain a made-up amount.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
METRICS_PATH = REPO_ROOT / "docs" / "metrics.json"

_DOLLAR = re.compile(r"\$[0-9][0-9,]*(?:\.[0-9]+)?")


def _strip_code(text: str) -> str:
    """Remove fenced code blocks and inline code spans so examples are not checked."""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]*`", " ", text)
    return text


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def check() -> list[str]:
    payload = json.loads(METRICS_PATH.read_text())
    anchors: dict[str, list[str]] = payload["anchors"]
    dollar_values: set[str] = set(payload["dollar_values"])
    documents = payload["checked_documents"]

    prose_by_doc: dict[str, str] = {}
    for rel in documents:
        path = REPO_ROOT / rel
        if not path.exists():
            prose_by_doc[rel] = ""
            continue
        prose_by_doc[rel] = _strip_code(path.read_text())

    combined = _normalise(" ".join(prose_by_doc.values()))
    failures: list[str] = []

    # Forward: each metric's value must be stated somewhere with an anchor phrase.
    for name, phrases in anchors.items():
        if not any(_normalise(phrase) in combined for phrase in phrases):
            failures.append(
                f"metric '{name}' is not stated with a current anchor phrase "
                f"in any checked document (expected one of: {phrases})"
            )

    # Reverse: every dollar figure in the docs must be a produced metric value.
    for rel, prose in prose_by_doc.items():
        for token in _DOLLAR.findall(_normalise(prose)):
            normalised = token.rstrip(".")
            if normalised not in dollar_values:
                failures.append(
                    f"{rel}: dollar figure {normalised} matches no metric in metrics.json "
                    f"(guarded figures are {sorted(dollar_values)})"
                )

    return failures


def main() -> int:
    if not METRICS_PATH.exists():
        print("docs/metrics.json is missing: run tools/collect_metrics.py first", file=sys.stderr)
        return 1
    failures = check()
    if failures:
        print("check_numbers FAILED:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("check_numbers passed: every document figure is produced by the code")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
