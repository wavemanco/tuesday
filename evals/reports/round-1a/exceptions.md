# Round 1a: infrastructure exceptions (manifest section 14: cap 0, each goes to the owner)

## E-1. Session restart cost twelve Sonnet runs (17 November, 14:44 to 14:50 UTC)

- What happened: the cloud session restarted at about 14:44 UTC. The machine did not reboot (uptime unbroken),
  and the step's driver, both run_fixtures processes and the 95% guard kept running.
  - 14:44:33-34: every `claude -p` child that was mid-run received SIGTERM (return code 143) in the same second.
  - 14:48:25-14:50:08: the three runs that each runner started in their place, at 14:44:34, ended on
    "Authentication error · This may be a temporary network issue, please try again" after a few turns.
  - From 14:54 runs complete normally (mock-interview-6.run4 in both installs, and every later part).
- Affected runs (Sonnet, existing mock-interview rooms, part-2; no new room, no core screen, no zero bar,
  no E23 replay, no job-underwriter run):

  | Install | Killed at the restart (rc 143) | Authentication error after it |
  |---|---|---|
  | tuesday | mock-interview-5.run3, mock-interview-5.run4, mock-interview-6.run0 | mock-interview-6.run1, run2, run3 |
  | alone | mock-interview-5.run3, mock-interview-5.run4, mock-interview-6.run0 | mock-interview-6.run1, run2, run3 |

- How the runner recorded them: outcome `declined`, harness-invalid, reason "skipped: CLI declined: ...",
  `limit_hit` false, metas written. The runner's own killed-run survey (`killed_survey`) classes a run as a
  restart kill only when no meta exists (the runner itself died), so it reads all twelve as `declined`
  set-asides, never rerun.
- Manifest reading: section 14 treats a container restart as a kill, rerun at once under its own stems;
  the frozen recovery path does not cover a restart that kills the CLI but not the runner, nor the
  authentication failures that followed it.
- Effect if left as set-asides: mock-interview case 6 keeps 1 of 5 runs per install (run0-3 lost, run4 kept)
  and case 5 keeps 3 of 5; the Sonnet regression panel for mock-interview has 44 instead of 50 candidate runs
  per install. Set-aside share per install rises by 6 of 145 from this alone.
- Rerun cost if the owner wants it: twelve Sonnet runs plus two grades each, about $12 at part-2's rate
  ($0.86 a run, $0.15 a run to grade), under one point of the weekly meter.
- Not done: no file moved, nothing rerun. Disposition: the owner's.

**Disposition (owner, 17 November, after the Sonnet step):** leave the twelve runs as set-asides; nothing rerun.
Recorded as exception E-1 with that disposition.
