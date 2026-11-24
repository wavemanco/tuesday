# Measurement round reports

This folder keeps the reports from the measurement rounds: what was put to the owner, how each grader event was ruled
on, and the tallies behind them. Each round has its own folder. What a report said when it was delivered is kept as
it was; anything added later is marked as added.

| Folder | Round | Result |
|---|---|---|
| `round-1a/` | Round 1a, 17–19 November: candidate `bb96307` on Haiku and Sonnet | The bar was missed on both models; Opus and the explicit panel were skipped by the owner's decision |
| `round-1a-2/` | Round 1a-2, 19–20 November: candidate `43fc223` on Haiku and Sonnet | The bar was missed on both models; the round stopped under the owner's plan, before the explicit panel and Opus |
| `round-1a-3/` | Round 1a-3, 20 November: candidate `1877a75` on Haiku and Sonnet | The bar was missed on both models (Sonnet passed every core screen; one party-accusation run); the round stopped under the owner's plan, before the explicit panel and Opus |

## What a round folder holds

- **The reports.**
  - `round-1a/`:
    - `report-after-sonnet.md`, the state after the Sonnet step;
    - `adjudication-summary.md`, the rulings and the leads for the fix;
    - `exceptions.md`, the infrastructure exceptions;
    - `owner-decisions-17-november.md`.
  - `round-1a-2/` and `round-1a-3/`:
    - `report.md`, the whole round;
    - `independent-recheck.md`, the second reader's report, as returned.
- **`adjudications.jsonl`.** One line per grader event:
  - `A###`: zero-gate and leak (backstop) events;
  - `Q###`: core quote events;
  - `S###`: the sentinel scan's own hits.

  Each line gives:
  - the run, the expectation and the grader;
  - the grader's finding, verbatim;
  - the passage and its surface;
  - the ruling and the rubric step that decided it;
  - a reason and a confidence;
  - `owner_review`.

  From round 1a-2 on, the zero-gate lines also carry `independent_recheck`.
- **`scores/`.** The tallies as each scorer printed them:
  - `<model>-score.txt` and `.json`, the core screens, gates and health checks;
  - `item-<model>.txt`, the carried item;
  - `compare-<model>-<install>-part-<n>.txt`, the regression comparison against the baseline;
  - `quotecheck.jsonl`, the script's quotation checks;
  - for round 1a, `core-whys.txt`;
  - for round 1a-3, `located-account-email.json`, where the account email sat in each run that holds it, found from
    the sealed stream with the value itself never written.
- **`scripts/` and `recheck/`.** The scoring and adjudication scripts, and the independent reader's scripts. They read
  the measurement folder (`/var/tmp/tuesday-measure/<round>/` on the machine that ran the round). That folder is not
  in the repository, so the scripts document how each number was reached rather than run from a fresh clone.

## Where the rest lives

- **The runs themselves are not in the repository.** That means every run's output, checks and grades, and the
  sealed copy of each step. They are large.
- **Section numbers in the reports** (for example "section 13" for adjudication, "section 14" for recovery) refer to
  the round's measurement manifest. Round 1a's manifest is in `1a-version-c-whole-verdict.tar.gz` on the data branch
  (`claude/skill-job-underwriter-95xjz8-data`). The manifests of rounds 1a-2 and 1a-3 are not backed up there yet.
- **Some run output keeps an old name.** A few compare files print the install name that the baseline recorded
  before the code-name rename. The files are kept as the tool printed them.
