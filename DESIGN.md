# DESIGN.md

## What I chose to measure, and why

The three variants all fail in ways that show up directly in the output structure.

- Variant A silently drops the `risk_assessment` field 30% of the time. 
- Variant B bypasses the risk service entirely and always returns a stub. 
- Variant C inflates the `summary` field with a fixed marketing prefix every single time. 

None of theserequire an LLM to detect — they are objectively measurable.

I chose deterministic structural checks for two reasons. 

First, the bugs are visible in the data: a missing field, a `None` score with no error 
explanation, a summary over 300 characters. 

Second, a production gate needs to give the same verdict every
time for the same input. LLM judges introduce variability — the same output could
pass one day and fail the next depending on model mood, temperature, or prompt drift.
That is not acceptable for something that blocks or approves a deploy.

The checks are split into two severity levels. 
- Critical checks cover data integrity and fraud detection — if any of these fail, 
the variant does not ship. 
- Advisory checks cover format contracts — if only these fail, the variant is flagged 
as Conditionally Safe, meaning it can ship only if the product team explicitly accepts 
the trade-off. Variant C lands here: all the important data is intact, the summary is 
just too long.

I also added three checks that none of the current variants trigger: that the output
`order_id` matches the input, that the risk `recommendation` is a known valid value,
and that the shipping output has the expected internal structure. These exist to catch
the possible future regression.

Variant A runs 10 times per order. Its bug fires ~30% of the time, so a single run has
a 70% chance of missing it. At 10 runs the miss probability drops to 2.8%, which is
acceptable without LLM cost concerns. Variants B and C are deterministic, so 3 runs
is enough to confirm the bug is not noise.

## What this eval would not catch

**Semantic accuracy of the risk score.** If someone changes the scoring formula and it
returns a plausible number — say 0.42 instead of the correct 0.71 — every check passes.
The eval verifies that a score exists and is in range, not that it is correct for a
given customer and order amount. Catching that would require a reference dataset with
known expected scores.

## Cost and runtime per run

Right now the cost is zero. All tools are local and simulated — no network calls, no
external APIs. A full run (380 total calls across all variants) completes in under 10
seconds on any laptop.

If I added an LLM judge for semantic quality checks — for example to verify that the
summary text actually makes sense — the cost would still be low but not zero. Each call
would need around 200–300 tokens. At 380 calls that is roughly 95,000 tokens total.
Estimated cost by model:

| Model | Input price | Estimated cost per run |
|---|---|---|
| Gemini 2.0 Flash | $0.10 / 1M tokens | ~$0.01 |
| GPT-4o mini | $0.15 / 1M tokens | ~$0.02 |
| Claude Haiku 3.5 | $0.80 / 1M tokens | ~$0.08 |
| Claude Sonnet | $3.00 / 1M tokens | ~$0.29 |

For this task a basic model is more than enough. Checking whether a summary is
coherent and within a reasonable length does not require a frontier model. I would use
Gemini Flash or GPT-4o mini and keep the cost under $0.05 per full run.
