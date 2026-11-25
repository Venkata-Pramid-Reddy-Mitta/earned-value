# ADR-001: Earned value against a baseline, not a burn-up of spend

Status: accepted

## Context

The usual artefact for tracking a delivery program's cost is a burn chart: cumulative actual spend
plotted against a planned cost baseline. It is one line against another, and the gap between them is
a single scalar per week. A program reported as "spend within 5% of budget" is a statement about that
gap alone.

A single scalar cannot distinguish two states that a status owner must never confuse: under budget
because the team is efficient, and under (or near) budget because the scheduled work has not yet been
done. On a staffed program the second state is common and the burn chart is blind to it.

## Decision

Compute earned value (the budgeted cost of work actually completed) as a first-class third measure
alongside planned value and actual cost, and derive the standard PMI indices from it: CPI, SPI, EAC,
VAC, TCPI. Attribute the burn gap with the identity
`actual_cost - planned_value == schedule_variance - cost_variance`, which holds every week to a
**maximum residual of 0.00** dollars.

## Alternatives considered

- **Burn-up of spend only.** Rejected: it is exactly the artefact whose blind spot this project
  exists to expose. Keeping it as the only view would reproduce the problem.
- **Schedule variance in time units from the start (Earned Schedule).** A real improvement near the
  finish, but it changes the subject from the classic decomposition and hides the teaching point that
  SPI in dollars goes blind. Deferred to a boundary (ADR-003) so the blindness is measured, not
  papered over.

## Consequences

The tool requires one input a burn chart does not: a percent-complete per task. That input is also
the main way earned value is gamed in practice, which is called out in ADR-004 and the README
boundary section. In exchange, the single ambiguous spend gap becomes two attributable numbers, and
the weeks where spend read healthy while the schedule was late become countable: **14 reporting
weeks** on the committed fixture.
