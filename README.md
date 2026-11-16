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
| `1a-harness-recheck.tar.gz` | The fix round's 1,220 saved runs re-checked by round 1a's harness commit (`759a7ca`, read from its snapshot, not a working tree): every run's checks file, the nine arm comparisons, the log against the quote-list re-check and the script. 2 checks files differ, both already failing |
| `1a-harness-design.tar.gz` | Round 1a harness's design, its adversarial critique and the decisions made on its open questions (16 November), with the run log and meter readings through 16 November 13:57 UTC |
| `1a-candidate-build.tar.gz` | Round 1a's candidate, built and verified outside the repository on 16 November: its design (five slice designs, the consolidated spec and two critiques), the build that applied the accepted fixes, three adversarial reviews and their resolution, the final verification from a fresh copy, and the patches (`H.patch`, the harness follow-up pushed as `86fce3f`; `C.patch`, the candidate). Also the draft priced manifest and its inputs: false-miss estimates, the adjudication rule, the baseline re-check under the pinned harness (checks files only) and the grade-gap report. Copies of the repository are left out; the patches rebuild them |
| `1a-candidate-variant-b.tar.gz` | The second version of round 1a's false-accusation bar, for the owner's choice: in the four warning-sign cases a scam label on the request alone is counted and reported instead of failing the release. Only the two test files differ from the first version; the shipped skill text and its digests are the same. With its review, its patch (`C-b.patch`) and the owner summary and draft manifest as of 16 November 20:00 UTC |
| `baseline.tar.gz` | The earlier quality check the fix round is scored against, on all three models, with its scoring scripts |

Left out on purpose: the full model transcripts and each run's working folder or room, which are large and not needed to score the round. In three baseline runs the model copied the account owner's email address into a tool call; it is replaced with `[account email removed]` here.
