# ADR-004: The committed fixture is the artifact, not the generator

Status: accepted

## Context

The project promises that a reviewer reproduces every published number with one offline command. The
numbers are produced from a seeded generator that draws per-task productivity and cost factors from
numpy. numpy's `Generator` stream is stable within a version but is not guaranteed bit-for-bit
identical across every future numpy release.

## Decision

Treat the committed `data/program.csv` as the authoritative artifact. `make verify`, the experiments,
and the metrics collector all read that file; none of them regenerates it. `make regen` exists to
rebuild the fixture but is deliberately excluded from `verify`, and the README says that reproducing
the published figures from a fresh draw requires the pinned numpy.

This also fixed a real bug. An early check asserted the reloaded fixture earned exactly the budget;
it did not, because money written to six decimal places does not sum back to an exact dollar. The
fixture is priced as decimal text and checks use a cent tolerance;
`test_the_csv_round_trip_needs_a_cent_tolerance` pins it.

## Alternatives considered

- **Regenerate inside verify.** Rejected: a numpy stream change would silently alter every published
  figure and the number checker would then fail against the README, turning a dependency bump into a
  confusing red build about numbers that were never about the code.
- **Pin numpy to an exact version.** Helps, but a committed fixture is stronger: it needs no trust in
  the pin and works even if the generator is later refactored.

## Consequences

The one input the tool declares rather than observes is percent complete per task, encoded by the
generator. Against a real program the arithmetic is identical and only the inputs change. Percent
complete is also the main way earned value is gamed in the field, so a real deployment would need an
independent check on it; that is out of scope here and noted as such.
