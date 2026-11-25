# Defense guide: earned-value

## The 30 second version

"A burn chart plots spend against plan. That gap is one number, and one number cannot tell under
budget from behind schedule. I built the earned-value decomposition that splits it, and ran it over a
seeded $2,500,000 program. It found 14 reporting weeks where spend was within 5% of budget while the
schedule was already late, and the worst week hid $73,506 of work that was scheduled and never
earned. The program finished $339,975 over budget at a CPI of 0.880, and the cost forecast saw that
from week 1." Then stop. The question that usually comes next is "so why doesn't everyone just use
earned value?", which is the opening for the SPI blindness boundary.

## The claims and how each is proved

### Claim 1: the spend gap decomposes exactly

- Command: `python experiments/decompose_the_gap.py`
- Numbers: the identity `actual_cost - planned_value == schedule_variance - cost_variance` holds to a
  **maximum residual of 0.00** dollars across every week.
- If pushed ("is that just algebra?"): yes, the identity is algebra, and that is the point. The value
  is that earning value separately is what makes the two terms computable at all. Without EV you have
  the left side and no way to split the right.

### Claim 2: fourteen weeks read healthy while the schedule was late

- Command: `python -m earned_value.cli illusions`
- Numbers: **14 reporting weeks**; worst concealed slip **$73,506** at **week 22**; final **CPI of
  0.880**.
- If pushed ("you chose the 5% and 0.95 thresholds to get a big number"): both live in `config.py`
  and the test `test_custom_tolerances_change_the_verdict` shows the verdict moves with them. The 5%
  band is taken straight from the "spend within 5% of budget" status language; 0.95 is a conventional
  SPI watch line. The point is not the exact count, it is that the two reads disagree for a stretch of
  the program.

### Claim 3: the cost forecast was early

- Command: `python experiments/forecast_vs_final.py`
- Numbers: final overrun **$339,975** (**13.6%** of budget); EAC was **within 5% of the final cost by
  week 1**.
- If pushed ("CPI being flat is an artefact of your generator"): correct that a flat CPI makes EAC
  stable early, and a real program's CPI wanders more. The defensible claim is narrower: whenever CPI
  is even roughly stable, EAC leads the burn gap, because EAC reacts to efficiency while the gap also
  moves with schedule.

### Claim 4: the tool's own schedule read goes blind at the finish

- Command: `python experiments/spi_blindness.py`
- Numbers: **SPI trough 0.883** at week 3, **SPI recovers to 0.989** at the planned end, **SPI of
  1.000** at completion in **week 41**. CPI never recovers.
- If pushed ("then your tool is broken near the end"): the schedule half of it is, structurally, and
  that is why the limitation is published rather than hidden. The fix is Earned Schedule, which is the
  named Pivot and is deliberately out of scope.

## Questions that are meant to be hard

- **Is this just a wrapper around a formula?** The formulas are standard PMI. The original work is the
  illusion detector (classifying each week by two independent reads and pricing the concealed slip in
  dollars), the staffing mechanism that makes the illusion real, and the receipts harness that fails
  the build if a document drifts from the code. The arithmetic is deliberately unoriginal; building on
  a known standard is the right call for a governance tool.
- **The data is synthetic, does any of it transfer?** The arithmetic is identical against a real
  program; only the inputs change. What is synthetic is the scenario, and it is one scenario, stated
  in ADR-002. The one declared-not-observed input is percent complete per task.
- **What is the weakest part?** The reliance on percent complete. Earned value is only as honest as
  that input, and in the field it is the number most often gamed (the "90% done for months" problem).
  This tool takes it as given from the fixture and does not audit it. A real deployment would need an
  independent completion signal, and I would not claim otherwise in a status meeting.
- **What would you do differently with more time?** Build Earned Schedule so the schedule read
  survives the final weeks, load a real Azure DevOps or MS Project export instead of the generator,
  and put a confidence band on EAC instead of a single point.
- **Why should a PM trust a number you computed over the one in their dashboard?** They should trust
  neither on faith. The whole repository is built so every number is reproduced by one offline
  command and re-checked by CI, which is the opposite of a dashboard figure nobody can trace.

## Things to say, and things not to say

Say:

- "The burn chart is not blind forever, it is blind early, when you could still act."
- "The illusion count depends on the thresholds, and the thresholds are config, not hidden."
- "SPI near the finish is not a schedule signal, and I will not read it as one."

Do not say:

- "This proves real programs are mismanaged." It proves one metric is insufficient, on one seeded
  scenario.
- "Earned value catches everything." It does not catch a dishonest percent-complete, which is its own
  weakest input.
- "SPI of 1.000 means on schedule." At completion it means nothing about lateness.

## The live demo script

```bash
python -m earned_value.cli report --week 22        # the worst concealed week in full
python -m earned_value.cli gate --week 5           # exit 1, and the note that the burn chart reads healthy
python -m earned_value.cli gate --week 40          # exit 1, overspend now visible on the burn chart too
python -m earned_value.cli illusions               # 14 weeks, worst $73,506, final CPI 0.880
python experiments/spi_blindness.py                # the uncomfortable headline, SPI recovering to 1.000
```
