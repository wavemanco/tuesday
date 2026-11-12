# What the measurements cost

## What the figures mean

Every model call in this repository's measurements, the runs and the graders alike, went through Claude Code (`claude -p`) signed in to a Claude subscription account, never with an API key. Every saved run transcript, 2,338 of them, reports `apiKeySource: none`; the graders run through the same `claude` command on the same sign-in, and their output records no key source either way. Nothing in the repository calls the Anthropic API directly, and nothing was billed per token.

- **Dollar figures are an API-price equivalent, not money spent.** Claude Code reports, with each run, what the same tokens would have cost at API list prices: `total_cost_usd` on each run, `costUSD` on each grader. The figures below add those up. They are useful for comparing one measurement with another.
- **What a measurement really uses is the subscription's weekly usage limit.** Usage is given in points, meaning percentage points of the account's seven-day usage meter. The meter resets weekly. When it reaches 100%, runs stop until the reset.
- **The meter counts the whole account.** Other use of Claude on the same account in the same week moves it too, as does the Claude Code session that runs and writes up the measurement.
- **The meter reads in whole percents.** A step that moves it a few points has a wide range of dollars per point: the Haiku quality step's 2 points could be anywhere from about $12 to $37 a point.

If you run the evals yourself with `ANTHROPIC_API_KEY` set, Claude Code uses the key, and those runs are billed per token at API prices.

## Measurements with a recorded cost

The names are those of the README's Tracked work entries.

| Measurement | Models | Runs and grades | API-price equivalent | Weekly usage | $ per point |
|---|---|---|---|---|---|
| Quality through Tuesday, Sonnet | Sonnet 5.5, graders Sonnet | 230 runs, 460 grades | $170.05 | 9 points (15% to 24%) | $18.9 |
| Quality through Tuesday, Haiku | Haiku 5.5, graders Sonnet | 230 runs and 8 re-runs, 460 grades | $37.43 | 2 points (28% to 30%) | $18.7 |
| Quality through Tuesday, Opus | Opus 5.5, graders Sonnet | 230 runs, 460 grades | $285.73 | 11 points (31% to 42%) | $26.0 |
| The fixed harness, smoked on Sonnet and Opus | Sonnet 5.5 and Opus 5.5, graders Sonnet | 52 runs, 104 grades | $70.35 | 3 points (45% to 48%) | $23.5 |
| Fix round, Haiku | Haiku 5.5, graders Sonnet | 460 runs and 15 re-runs, 920 grades | $72.79 | 10 points (62% to 72%) | $7.3 |
| Fix round, Sonnet | Sonnet 5.5, graders Sonnet | 380 runs, 760 grades | $283.72 | 15 points (73% to 88%) | $18.9 |
| Fix round, Opus | Opus 5.5, graders Sonnet | running | — | — | — |

- **Re-runs.** When a run does not start its module, the harness runs it again with the module named. Both sessions are counted in the cost; only the final one is graded, twice, as every run is.
- **Opus costs more per point** at the fix round's own planning rates, which convert the API-price equivalent to weekly usage at $17 to $21 a point for Sonnet and Haiku and $24 to $29 for Opus (`docs/fix-round-plan-detail.md`). Its stop rule uses those rates.
- **The fix round's Haiku step shared its week with other use of the account.** At the planning rates its runs account for about 4 of its 10 points.
- **The Sonnet quality step's** meter window also holds a two-run check worth $0.76, which its row leaves out.

The dollar figures in both plan documents, such as "about $1,070 of runs", are API-price equivalents in the same sense.

## Measurements without one

- **The routing rounds** saved no cost per run: the entries "Tuesday, measured on three models", "Tuesday, round 2" and "Tuesday, round 3". Round 3 ran into the weekly limit 38 minutes in, at 17:46 UTC on 31 October, and the runs it stopped were re-run on 5 November.
- **The fixture rounds before them** (rounds 7 to 9 and the watch-out round) saved each run's cost but took no meter readings, so they are left out here.

## Where the figures come from

- **Run records:** each run's stream ends with a result event carrying `total_cost_usd`, and the run's `*.meta.json` keeps the same cost in its invocations' `modelUsage`. Each grade file carries the grader's `model_usage` with `costUSD`.
- **Meter readings:** taken before and after each step.
- **Backup:** the meta and grade files for the fix round and the quality check, without the transcripts, are kept on the branch `claude/skill-job-underwriter-95xjz8-data`. The smoke's records are not on it.
