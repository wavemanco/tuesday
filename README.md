# Fix-round measurement data

This branch is a backup, not part of Tuesday. It holds the scoring data for the fix round planned in `docs/fix-round-plan.md` (on the pull request branch), so the round can be scored even if the machine that ran it is lost. It never merges into `main`.

| File | What it holds |
|---|---|
| `fix-round-haiku.tar.gz` | The fix round on Haiku: every run's output, its checks and both grades, per module, with Tuesday and with the module alone |
| `fix-round-sonnet.tar.gz` | The same on Sonnet |
| `fix-round-opus.tar.gz` | The same on Opus, added when that step finishes |
| `fix-round-scripts-and-logs.tar.gz` | The scripts that ran the round, its run log, meter readings and pre-flight checks |
| `baseline.tar.gz` | The earlier quality check the fix round is scored against, on all three models, with its scoring scripts |

Left out on purpose: the full model transcripts and each run's working folder, which are large and not needed to score the round. In three baseline runs the model copied the account owner's email address into a tool call; it is replaced with `[account email removed]` here.
