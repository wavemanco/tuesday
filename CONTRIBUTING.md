# Contributing

Two rules protect this repository's structure; everything else is ordinary.

## Per-path licensing

Grants are per-directory (see the root LICENSE map). A contribution is made
under the license of the directory it lands in. Do not move files across
license boundaries in the same change that modifies them.

## agent/ contributions require a CLA

The (future) agent/ directory is planned as AGPL-3.0 with dual-licensing
optionality retained by the maintainer. To preserve that option, contributions
to agent/ will require a contributor license agreement assigning or broadly
licensing the contribution to the maintainer. This clause exists from day one
so it never has to be retrofitted across a contributor history.

## Fixing what the evals find

A clean-room failure can be fixed by rewording the rule or by changing the shape
of the output. Choosing wrong is expensive, and the choice has a mechanical
trigger rather than a judgment call.

**A deterministic failure means stop rewording.** `evals/run_fixtures.py`
classifies every failure as `deterministic` (it failed every run) or
`intermittent`. Treat them differently:

- **Intermittent** — a reliability finding. The rule fired once and not another
  time, so rewriting it is as likely to move the number by luck as by fixing
  anything. Reword it if the wording is genuinely unclear, or record the rate.
- **Deterministic** — the rule is not reachable from where the writer stands. It
  is allowed one rewording; if it fails deterministically again, the next fix
  changes the shape of the output, not the sentence describing it.

**What decides which kind of fix works.** Prose can change what goes *into* a slot
the writer is already filling. It cannot reliably create the noticing of a slot
that is not there. So:

> **When compliance depends on noticing an absence, or on comparing two things
> the output does not place side by side, the fix is a slot, not a sentence.**

A slot is a cell, column, or required field that is **visibly empty when
unfilled**. The test: would a compliant and a non-compliant output differ at a
glance? If not, prose will not hold it.

**This is not "prose does not work."** Six prose fixes in one session closed
deterministic failures on the first attempt — a named absence needing a second
half, a premise needing correcting at a named moment, a trace cell needing
quotations rather than references, a question budget needing a counting rule.
Every one of them changed what goes into something already being written.

The ones that needed a slot all failed the test above:

| Failure | Prose attempts | What fixed it |
|---|---|---|
| Provenance labels going missing | 4 | Its own column, in three sections |
| Register entries losing verification questions | 1, then deterministic | A column; only `positive_signal` rows may leave it empty |
| Application-plan advice unlabelled and unmarked | 1, then deterministic | A table with Provenance and Status |
| Guidance promoting "ran" into "built" | 1, then deterministic in every run | The Provenance cell carries the candidate's quoted sentence beside the label |
| Banks not covered against the JD's own list | 1, then deterministic | A requirement-coverage table with question IDs and "none, and why" |

Each of those asked a writer to spot something absent, or to compare two things
sitting in different parts of the document. A cell that cannot be filled is the
finding, not an inconvenience.

**A worked example is part of the rule.** Whatever the reference file says, the
worked example is what gets copied — so an example that violates its own rule
teaches the violation. One in this repository did: an edit-ledger row whose trace
cell read "same line, moved above the UAT bullet", one screen below the rule
forbidding exactly that. Check examples against the rule they illustrate, and when
one has taught a defect, say so in the example rather than silently correcting it.

## Structural rules

- Skills are dependency-free: nothing outside a skill's folder may be required
  at runtime. Agent tooling never leaks into skills/.
- conventions/ is canonical. Skills carry mirrors in references/ with a
  synced-from header; a mirror that drifts from canonical is a defect, and the
  fix flows canonical -> mirror, never the reverse.
- Every skill upholds the standalone invariant (interaction-grammar.md §1).
- Every skill folder carries its own LICENSE copy, so packaged .skill files
  and zips remain self-describing when they travel detached from the repo.
