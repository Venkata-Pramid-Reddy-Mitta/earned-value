# ADR-005: Exit codes that distinguish "no" from "cannot answer"

Status: accepted

## Context

The `gate` command is meant to be usable in a pipeline: run it on a reporting week and let the exit
code drive a decision. A gate that returns the same failure code for "I ran and the week is not
healthy" and "I could not run because the fixture was malformed" is untrustworthy, because a
misconfiguration would read as a clean red light and a real problem could be mistaken for a bad
argument.

## Decision

Three exit classes, documented in the README and enforced by tests:

- `0`: the tool ran and the week is healthy on both the schedule and the cost read.
- `1`: the tool ran and the week is flagged, behind schedule or over cost.
- `2`: the tool could not answer, a bad argument or a missing or malformed fixture.

argparse already exits `2` on an argument error, so the usage class is consistent whether the failure
is a bad flag or a bad fixture. Input is validated at the model boundary, so a malformed fixture is
refused with a clear message rather than producing a quietly wrong curve.

## Alternatives considered

- **Boolean exit (0 or 1).** Rejected: it collapses the two failure meanings and makes the gate unsafe
  to automate.
- **Raise on a flagged week.** Rejected: a flagged week is a normal, expected answer, not an error. An
  exception would conflate it with a crash.

## Consequences

Callers can branch on the code: treat `2` as "fix the setup", `1` as "the week needs attention", `0`
as "clear". The tests `test_gate_on_a_flagged_week_exits_one`,
`test_gate_on_a_healthy_week_exits_zero`, and `test_gate_on_a_missing_fixture_is_a_usage_error` pin
each class.
