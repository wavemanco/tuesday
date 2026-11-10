# The fix round, in short

This is the short version of the fix round's plan and bar. The full version, with every
threshold, its calibration and the commands, is `fix-round-plan-detail.md`; where the
two differ, the full version holds. Both are in the repository before any measured run,
so the bar is fixed in advance.

## What the round does

**Before any run.** No model calls are spent here.

- **Harness changes**, as the owner decided:
  - runs may save inside their own test folder, in both arms;
  - a re-cut quote passes and is still reported;
  - a quick check of pasted material passes: at most two calls, each naming what it
    checks, and reported;
  - job-underwriter's fixture 5 stops saying when its pages were copied, since a
    typical user does not;
  - the scorer prints every measure the bar reads.
- **One text change** to what Claude reads:
  - the old working name goes from the three places Claude reads it;
  - Tuesday gets its row in the routing table, with a line saying to install Tuesday
    or the modules, never both;
  - both modules' research rules allow the quick check;
  - the one sentence allowed after job-underwriter's fit ledger becomes a short list,
    so two readings stay one sentence.

The text commit is pushed at once. CI stays red on it in one place, the guard that marks
text as not yet measured, until the round passes. That is the guard doing its job, and
the pull request is not merged meanwhile.

**The measured round**, after the weekly meter resets on Thursday 12 November at 06:00
UTC:

| When | What |
|---|---|
| Thursday | Quality on Haiku, then Sonnet |
| Friday | Quality on Opus |
| Sunday | Routing on all three models, with Opus case 10 and Haiku case 3 at 50 runs a side |
| Monday | Scoring and the report |

Quality runs every fixture of every module twice, once with the module alone and once
through Tuesday, both installed the same way: 1,120 graded runs. Routing is 870 runs.

## The bar

**Quality.** Per module and model, the module through Tuesday must not do worse than
alone. It misses when:

- its graded pass rate is more than 5 points lower;
- an automatic check fails in at least 10 points more of its runs (p below 0.01);
- a truthfulness check fails in at least 10 points more of its runs (p below 0.05);
- more than 10% of either arm's runs are set aside.

**The text change's own goals:**

- *More than one sentence after the fit ledger.* Today this happens in 39% of
  job-underwriter runs on Sonnet, 74% on Haiku and 81% on Opus. The goal is at most
  10% on Sonnet and Opus, and 20% on Haiku.
- *Research calls beyond a quick check.* The goal is at most 1 run in 10 on fixture 5,
  and at least 9 in 10 of the runs that make a call reporting every call.

Falling short of a goal does not block shipping: the issue stays open and is recorded.
Getting worse does block it.

**Routing** keeps round 3's items. A hidden module may be reached at most once across
all of the round's 1,025 Tuesday sessions. Two items were loosened because they would
often miss by luck: Haiku's single-module gain, and the "no module starved" margin.

**How far to trust a miss.** With nothing actually wrong, the bar would still flag
something about one round in four or five, mostly on Haiku. That comes from checking
nine module-and-model pairs and three routing comparisons at once. A flag goes to the
owner with its numbers and is not re-run away, so a false flag costs a decision, not
the round.

**What the bar sees poorly.** It sees moderate slips in job-underwriter and
resume-tailor poorly. A pass there means no large slip was seen.

**Outcomes:**

- **Pass:** the text is recorded as measured, the plugin moves to 0.2.0, and the README
  ledger gets the round.
- **Miss:** the owner gets every number and decides. No run is repeated to turn a miss
  into a pass.

## Cost

The round costs about 49 points of the weekly meter (43 to 54), about $1,000 of runs.
It should end near half the meter. No step starts above 80%.

## Left out

- Tuesday's description, which waits for a fourth module.
- A quoting change.
- A change to mock-interview's watch-out line.
- Regrading the saved runs.
- One folder per application, which is measured on its own next.
- Routing in the personal install.
- Surfaces no run reaches: claude.ai on the web and in the desktop app, live web
  research, live drills and second turns.

## Questions for the owner

1. **Run size.** The plan runs 10 runs per fixture on Haiku and on mock-interview, and
   5 elsewhere, for about 49 points. All at 5 runs costs about 33 points, with weaker
   checks. Recommended: the plan's size, plus resume-tailor at 10 on Sonnet and Opus.
   That adds about 3 points and $70, and stops two broken runs from tripping its graded
   item.
2. **The sentence after the fit ledger.** Recommended: keep "one sentence", written as
   a list. The alternative is to allow two sentences that each name their rows. That
   would have passed most saved runs, but it changes the rule instead of meeting it.
3. **Code names that hold the old name**, such as `--via frontdoor` and
   `MEASURED_FRONTDOOR`. Recommended: rename them in their own commit after the round,
   so the round measures with the harness tested here.
4. **resume-tailor's owed change of shape.** Recommended: decide after the round, from
   its traces rate.
5. **The false-flag chance of one round in four or five.** Recommended: accept it. A
   flag costs a decision, not a re-run, and lowering it means loosening items that
   caught real losses before.
