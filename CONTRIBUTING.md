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

**Three runs cannot tell you anything, and this repository has been fooled by
three.** The deterministic/intermittent split is only as good as the run count
behind it. One expectation read 0/6, 2/6 then 3/6 across three three-run sets and
looked like a clean upward trend; the next set, at five runs, read 0/10. The
trend was noise, and it had already been written up as a first. A 50% failure and
a fixed one are indistinguishable at n=3 — both produce runs that pass. Use
`--runs 5` at minimum before calling anything closed, and prefer comparing two
sets that differ by exactly one change over comparing a set to its predecessor
three commits back.

**Labeling one free-text surface moves the claims to the next one.** The single
most useful thing five run-sets produced was not a fix, it was a migration path.
Unlabeled world-claims started in free prose, and each time a surface was given a
Provenance cell they reappeared in the next surface that lacked one: the risk
register's hypotheses, then the evidence map's reasoning cells, then the two
ledger slots that had replaced the decision snapshot's paragraph. Nothing is
regressing when this happens — the claims have to go somewhere, and they go
wherever free text is accepted without a label. Two consequences worth carrying:
a new free-text column ships with its Provenance cell in the *same* commit, never
the next one (CI enforces this, because the mistake was made twice in one
session); and a fix to this class is not verified by the failure count dropping,
it is verified by the graders naming a surface that no longer exists.

## Harnesses report three outcomes, not two

An eval harness runs external processes that can decline: time out, hit a rate
limit, return a truncated reply, exit non-zero. **Every path where that can happen
needs an explicit third outcome beside success and failure**, and it needs a test.

The rule is written from four bugs, all in this repository's own harnesses, all
the same mistake wearing different clothes — a non-result recorded as a result:

| What declined | What it was recorded as | What it should have been |
|---|---|---|
| The reader, exiting before parsing the pipe's tail | `neither` — the skill did not fire | the fire it had already streamed |
| A run the CLI failed, usually a rate limit | `neither` | `error` |
| A grader reply truncated mid-object | twelve expectations failed | the verdicts it did contain, marked truncated |
| A session usage-limit message | a 48-character response, graded | a skipped execution with a reason |

Each was found by a person reading output that looked wrong, which is the slowest
detector available and the one that fails silently when the output looks
*plausible*. The third of them produced a column of `errored` rather than a column
of low scores, which is the previous fixes working — but nothing stopped the run
from being started, and nothing would have caught a regression.

`evals/test_harness.py` covers each decline path and runs in CI. It is
standard-library only and spends no model calls, because every function it tests
is pure by design: where a decline path is buried inside a subprocess loop, extract
the classification so it can be tested rather than leaving it untestable and
therefore untested.

A test that cannot fail is worse than no test, so each of the four bugs above was
reintroduced against the finished suite and confirmed caught before this was
written down.

## The documentation is graded too

A skill's output is graded: every line traces to a quoted source in a cell, and
evals check it. Until this rule existed nothing else was — not the conventions
imposing that discipline, not the ledger describing them, not the specs, and not
the self-test certifying the checks. Twenty-one findings over three review panels
came from that exempted zone, and none was caught by its author. The discipline
now applies to the documents that state it.

**A claim about the outside world is cited, and its quotation is verbatim.**
`conventions/citations.md` holds each source sentence once, beside its source and
what weakens it. Prose cites it as `(cite C1)` and may quote only what the entry
holds. The paraphrase problem is a comparison problem: a restatement in one file
and its source in another are never read side by side, which is this document's
own test for when a sentence must become a slot. `check_skills.py --only
citations` verifies every marker resolves and every entry is used. A marker
covers every quotation earlier in its sentence, not only the one beside it, and
each must sit inside that marker's entry; curly quotation marks count. A
quotation with no marker is compared with every entry: found verbatim, it is a
source quoted without its citation; close to an entry but not inside it, it is a
paraphrase wearing quotation marks, which is how the original defect shipped.
`ci/verify_citations.py` refetches the sources and checks each entry against
them; it needs the network, so it runs by hand, and it reports *unreachable* as
unchecked rather than as a pass.

What it cannot see is a paraphrase with no quotation marks, or a quotation of a
source that has no entry — there is nothing to compare either with. Those still
need a reviewer.

**A reference into another file names that file; a bare §N means this one.**
Write it `name.md` §N — one spelling, so the check can resolve it. `--only
sections` resolves every reference. Thirteen bare references each meant some
other file — a parenthetical naming "the mirror" by section number, a table
column headed "Section of the mirror" — and the first version of the check only
asked whether this file had a section with that number. Fifteen more passed it
that way — the build brief sent readers to the grammar's eighth section by
number alone, and had an eighth section of its own. A bare §N is now refused
when a word beside it names another file or document, when its paragraph or list
item names another file, or when its label is another file's heading for that
number. What the check cannot read is a meaning carried by an earlier paragraph,
and it cannot tell a quoted example from a reference, which is why this paragraph
describes that parenthetical rather than reproducing it. A local reference in a
block that names another file is written "this file's §N".

**A count agrees with what it counts.** `--only counts` reads a count wherever
it introduces a list, a table, a heading's subsections, or a file's numbered
sections, and a lead-in hard-wrapped before its colon is read whole. It sums
every counted noun in the lead-in, so "four things it does, and one it refuses"
is five. The first version read one shape — count word first, colon on the same
line, bullets below — and passed eight others in this repository without a word.

A count restated in another file is checked when the file holding the list is
named in the same sentence or the one either side: "six axes" beside
`reframing-audit.md` is compared with that file's table. This is how README.md was found still describing
output-discipline.md by its old rule count after a sixth rule was added. It
cannot tell a quoted mistake from a claim, so a paragraph about one describes it
rather than repeating it. A restatement that names no file is not
checked, because "axes" means persona and question-type axes in mock-interview
and a check keyed on the word alone would misfire. Prefer not to add
restatements, and when you do, name the file. When the reframing audit's list
and its count disagreed, settling which was wrong meant reading all thirteen
places that state the count. The list was wrong; the twelve restatements had been
right throughout, and nothing but reading could have said so.

**The ledger points; it does not restate.** Name the file and section that
changed (`evidence-conventions.md` §5), and cite rather than quote a source. A
ledger entry restating a rule becomes a second copy of it, and this ledger once
asserted a rule and its retraction four bullets apart because the rule changed
and the copy did not.

**The self-test's baseline is the whole gate.** `ci/test_checks.py` used to run
one group on the clean repo and then print "clean repo passes". A mutation of a
group already failing proves nothing about the mutation.

## Structural rules

- Skills are dependency-free: nothing outside a skill's folder may be required
  at runtime. Agent tooling never leaks into skills/.
- conventions/ is canonical. Skills carry mirrors in references/ with a
  synced-from header; a mirror that drifts from canonical is a defect, and the
  fix flows canonical -> mirror, never the reverse.
- Every skill upholds the standalone invariant (interaction-grammar.md §1).
- Every skill folder carries its own LICENSE copy, so packaged .skill files
  and zips remain self-describing when they travel detached from the repo.
