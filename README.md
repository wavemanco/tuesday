# Fix-round measurement data

This branch is a backup, not part of Tuesday. It holds the scoring data for the fix round planned in `docs/fix-round-plan.md` (on the pull request branch), so the round can be scored even if the machine that ran it is lost. It never merges into `main`.

| File | What it holds |
|---|---|
| `fix-round-haiku.tar.gz` | The fix round on Haiku: every run's output, its checks and both grades, per module, with Tuesday and with the module alone |
| `fix-round-sonnet.tar.gz` | The same on Sonnet |
| `fix-round-opus.tar.gz` | The same on Opus |
| `fix-round-routing.tar.gz` | The fix round's routing step on all three models: each arm's results file and its log (today's skills, Tuesday and the explicit commands), and the 45-run extra cases, Haiku case 3 and Opus case 10 |
| `fix-round-scoring.tar.gz` | The round's scoring: the scorer, its scorecard and the nine arm comparisons, and the verification (blind re-scorers, the harness-fault hunt and the reported items) |
| `fix-round-quote-list-recheck.tar.gz` | The fix round's saved runs re-checked under the quote-list rule the owner chose on 16 November: every run's checks file, the nine arm comparisons read from them, and the re-check script. 8 of 1,220 checks files differ from the round's own |
| `fix-round-scripts-and-logs.tar.gz` | The scripts that ran the round, its run log, meter readings and pre-flight checks |
| `baseline.tar.gz` | The earlier quality check the fix round is scored against, on all three models, with its scoring scripts |

Left out on purpose: the full model transcripts and each run's working folder or room, which are large and not needed to score the round. In three baseline runs the model copied the account owner's email address into a tool call; it is replaced with `[account email removed]` here.
