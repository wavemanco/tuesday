# What the measurements cost

## What the figures mean

Every model call in this repository's measurements, the runs and the graders alike, went through Claude Code (`claude -p`) signed in to a Claude subscription account. No API key was used: every saved run reports `apiKeySource: none`, and nothing in the repository calls the Anthropic API directly. Nothing was billed per token.

- **Dollar figures are an API-price equivalent, not money spent.** Claude Code reports, with each run, what the same tokens would have cost at API list prices: `total_cost_usd` on each run, `costUSD` on each grader. The figures below add those up. They are useful for comparing one measurement with another.
- **What a measurement really uses is the subscription's weekly usage limit.** Usage is given in points, meaning percentage points of the account's seven-day usage meter. The meter resets weekly. When it reaches 100%, runs stop until the reset.
- **The meter counts the whole account.** Other use of Claude on the same account in the same week moves it too, as does the Claude Code session that runs and writes up the measurement. That is why the points per dollar vary below.

## Measurements with a recorded cost

| Measurement | Models | Runs and grades | API-price equivalent | Weekly usage | $ per point |
|---|---|---|---|---|---|
| Quality through Tuesday, Sonnet step | Sonnet 5.5, graders Sonnet | 230 runs, 460 grades | $170.05 | 9 points | $18.9 |
| Quality through Tuesday, Haiku step | Haiku 5.5, graders Sonnet | 238 runs, 460 grades | $37.43 | 2 points | $18.7 |
| Quality through Tuesday, Opus step | Opus 5.5, graders Sonnet | 230 runs, 460 grades | $285.73 | 11 points | $26.0 |
| Harness smoke before the fix round | Sonnet 5.5 and Opus 5.5, graders Sonnet | 52 runs, 104 grades | $70.35 | 3 points | $23.5 |
| Fix round, Haiku step | Haiku 5.5, graders Sonnet | 475 runs, 920 grades | $72.79 | 10 points (62% to 72%) | $7.3 |
| Fix round, Sonnet step | Sonnet 5.5, graders Sonnet | 380 runs, 760 grades | $283.72 | 15 points (73% to 88%) | $18.9 |
| Fix round, Opus step | Opus 5.5, graders Sonnet | running | — | — | — |

Runs count every model session, including the re-runs the harness makes when a run does not start its module. Each run is graded twice. In the fix round's Haiku step, the account's other use that week moved the meter as much as the runs did, which is why its points cost far fewer dollars than the rest.

The fix round's plan converts the API-price equivalent to weekly usage at $17 to $21 a point for Sonnet and Haiku and $24 to $29 for Opus (`docs/fix-round-plan-detail.md`), and its stop rule uses those rates. The dollar figures in both plan documents, such as "about $1,070 of runs", are API-price equivalents in the same sense.

## Measurements without one

The routing rounds that measured Tuesday's choice of module (rounds 1 to 3 in the README's Tracked work) did not save a cost per run, and neither did the rounds before them. Round 3 ran into the weekly limit 38 minutes in, on 31 October at 17:46 UTC; the runs it stopped were re-run on 5 November.

## Where the figures come from

The run records: each run's stream ends with a result event carrying `total_cost_usd`, and each grade file carries the grader's `model_usage` with `costUSD`. The meter readings were taken before and after each step. The fix round's and the quality check's run records are kept on the branch `claude/skill-job-underwriter-95xjz8-data`.
