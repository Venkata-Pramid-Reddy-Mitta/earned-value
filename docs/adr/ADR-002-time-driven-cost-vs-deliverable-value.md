# ADR-002: Cost accrues on the calendar, value accrues on deliverables

Status: accepted

## Context

For the illusion to be real rather than contrived, the generator must model why actual spend tracks
the planned baseline while earned value falls behind. If cost and value moved together, there would
be nothing for earned value to reveal.

## Decision

Model the two on different clocks, which is how a staffed delivery program actually behaves:

- **Cost accrues on the calendar.** A team engaged on a task is paid for every week it is engaged,
  at roughly the planned weekly rate, whether or not the week's deliverables landed.
- **Value accrues on deliverables.** Earned value is credited only for work actually completed. When
  a task's productivity runs below plan, it earns less than it spends each week and leaves a
  remainder that spills into slip weeks beyond the planned end, during which cost keeps accruing.

The per-workstream mean productivity is the one scenario lever. Cloud migration runs near plan; the
two build-heavy workstreams run below it. The engine then reports whatever this produces; no number
is placed by hand.

## Alternatives considered

- **Inject a schedule variance directly.** Rejected: it would hardcode the answer. The variance has
  to emerge from a mechanism a reviewer recognizes, or the demonstration proves nothing.
- **Random cost and value with a target correlation.** Rejected: harder to defend and less realistic
  than the staffing mechanism, which a delivery manager will recognize immediately.

## Consequences

The illusion is a consequence of the model, not an input to it. The same mechanism is what makes CPI
sit below 1 for the whole program and what pushes the final actual cost above the budget. It is also
the honest limit: the model assumes cost is purely time-driven, so a program with large materials or
license costs that are not calendar-paced would behave differently.
