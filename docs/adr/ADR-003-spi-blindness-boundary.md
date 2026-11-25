# ADR-003: The SPI blindness boundary, measured not hidden

Status: accepted

## Context

The schedule performance index is earned value divided by planned value. As a program finishes, both
converge on the budget at completion, so SPI converges on 1.0 no matter how late the finish actually
is. This is a well known limitation of classic earned value, and it is precisely the kind of thing a
portfolio project should lead with rather than bury.

## Decision

Do not work around the limitation. Measure it and publish it as the uncomfortable headline. The
`spi_blindness` experiment records the trajectory: the **SPI trough 0.883** at week 3, the recovery
to **SPI recovers to 0.989** at the planned end while work is still unfinished, and the exact
**SPI of 1.000** at completion in **week 41**, a week past the 40 week baseline. Alongside it, CPI
shows no such recovery, which is why the cost read stays trustworthy to the end and the schedule read
does not.

## Alternatives considered

- **Implement Earned Schedule now.** Earned Schedule measures schedule variance in time units and
  does not go blind at the finish. It is the right v2 feature, but building it here would remove the
  teaching point and expand the scope past one clean impossibility. It is the project's named Pivot,
  with the trigger: a stakeholder needing a trustworthy schedule read in the final stretch.
- **Cap the reporting horizon at the planned end.** Rejected: it would hide the blindness by never
  showing the weeks where it bites.

## Consequences

A user must not read SPI as a schedule-health signal in the last stretch of a program. The README
boundary section and the defense guide both state this plainly, and the gate command's output is
careful to attribute lateness to SPI only where SPI is still meaningful.
