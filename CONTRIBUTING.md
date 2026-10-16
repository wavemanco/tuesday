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
| Guidance promoting "ran" into "built" | 1, then deterministic in every run | The Provenance cell carries the candidate's quoted sentence beside the label. It stopped the promotion it was built for and certified the row's topic, not each clause: practices the role implies kept arriving beside a genuine quote, which the verbatim evidence column and the answer slot now address |
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
the same mistake wearing different clothes — a non-result recorded as a result.
The rows after those are the decline paths a research room and a pinned grader
added, written down before they could become bugs of their own:

| What declined | What it was recorded as | What it should have been |
|---|---|---|
| The reader, exiting before parsing the pipe's tail | `neither` — the skill did not fire | the fire it had already streamed |
| A run the CLI failed, usually a rate limit | `neither` | `error` |
| A grader reply truncated mid-object | twelve expectations failed | the verdicts it did contain, marked truncated |
| A session usage-limit message | a 48-character response, graded | a skipped execution with a reason |
| A grader reply covering six of sixteen expectations | ten unflagged gaps, the run summarised as if complete | the gaps listed as incomplete, re-asked once, and an expectation with an ungraded run reported as unresolved, never clean |
| A canned research room whose stub server never connected | a run that chose not to search | harness-invalid, replaced, and kept out of the run count |
| A run that fired another skill with the same base name | the installed skill's output | a nudge in a fresh room, and harness-invalid if it still does not fire |
| A run cut off by the timeout | a crash that ended the whole pass | a timed-out execution with its partial stream kept, and no nudge |

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
what weakens it. The paraphrase problem is a comparison problem: a restatement in
one file and its source in another are never read side by side, which is this
document's own test for when a sentence must become a slot. So a quotation of a
source is written one way, and `check_skills.py --only citations` holds it to
that way:

- in double quotation marks, straight or curly, and never as a blockquote;
- with its marker directly after it — `"…" (cite C1)` — and one entry per marker,
  stacked where a quotation draws on two;
- and nothing it quotes that its entry does not hold.

A quotation carrying a figure, in a sentence that has a marker but with none of
its own, fails; so does a malformed marker, and so does a marked quotation that
begins after its source's hedge ("may", "suggests") in a sentence that restates no
hedge. An unmarked quotation is compared with every entry: verbatim, it is a
source quoted without its citation; the entry's words around a different number,
it is a misquoted figure; three content words in a row from an entry without
being inside it, it is a paraphrase in quotation marks, which is how the original
defect shipped. Every marker must resolve and every entry must be used. `ci/verify_citations.py` refetches the
sources and checks each entry against them; it needs the network, so it runs by
hand, and it reports *unreachable* as unchecked rather than as a pass.

What it does not read: a paraphrase with no quotation marks; a quotation of a
source that has no entry; an unmarked quotation under three words with no figure
in it; a paraphrase sharing fewer than three content words in a row with its
source — the original defect, "favours established candidates", is that short;
straight single quotation marks, unless a marker follows them; and fenced code.
`citations.md` itself is not read, because it records past paraphrases on
purpose. Anywhere else, a past paraphrase is described rather than quoted — the
check cannot tell a quoted mistake from a claim.

**A reference into another file names that file; a bare §N means this one.**
Write it `name.md` §N — one spelling, so the check can resolve it; a list of
section numbers after one file name is read against that file. `--only sections` resolves every
reference. Thirteen bare references each meant some other file — a parenthetical
naming "the mirror" by section number, a table column headed "Section of the
mirror" — and the first version of the check only asked whether this file had a
section with that number. Fifteen more passed it that way — the build brief sent
readers to the grammar's eighth section by number alone, and had an eighth
section of its own. A bare §N is now refused when the five words before it in
its clause name another file (hyphenated or spelled with spaces) or a document
("the grammar", "the schema"), when a skill's name sits directly beside it
outside that skill's own spec, when its paragraph or list item names another
file that has numbered sections, or when its label is another file's heading for
that number — unless its label is this file's own heading for it. A statute's §
is not a section. A local reference
that would otherwise read as another file's is written "this file's §N" or "§N of
this spec". What the check cannot read is a meaning carried by an earlier
paragraph, and it cannot tell a quoted example from a reference, which is why this
paragraph describes that parenthetical rather than reproducing it.

**A count agrees with what it counts.** `--only counts` reads a count in words, in
the shapes `counted_lists` in `ci/check_skills.py` names, and a lead-in
hard-wrapped before its colon is read whole. It adds a second count only in the
form "four things it does, and one it refuses", so "four bugs, found in two
harnesses" is four. A time span is never a count. The first version read one
shape and passed the others without a word.

A count restated in another file is checked when the text ties it to the file
holding the list — on the same line of a folder tree, after the file name and a
dash or colon, as its possessive, or as "the N rules in" it — and there a count in
digits is read too. "Six axes" after `reframing-audit.md` and a dash is compared
with that file's table; "two rules in" a file, or a count merely near its name,
is not read. Nearness was tried, and misread in both directions.
This is how README.md was found still describing output-discipline.md by its old
rule count after a sixth rule was added. A restatement that names no file is not
checked, because "axes" means persona and question-type axes in mock-interview
and a check keyed on the word alone would misfire. Prefer not to add
restatements, and when you do, name the file. When the reframing audit's list
outgrew its count, settling which to change meant reading every place that
states it, and the history of each — nothing but reading could have said
that the restatements had already moved to the new reading and the lead-in had
not.

**A skill's README draws its folder as it is.** `--only readmes` rebuilds each
README's folder tree from its indentation and compares the paths with the files
under `references/` and `evals/`, and checks a stated fixture count against
`evals.json` — written "N fixtures" or "N test cases". All three trees had
fallen behind the mirrors.

**A restated parameter agrees with its declaration.** `--only parameters` reads a
skill's `SKILL.md`, README, own references and eval expectations for two
restatements. A question budget in a sentence about the message, the turn or
asking must be `question_budget`; in mock-interview "questions" are mostly the
pack's interview questions, and those are not read. A clause whose subject is the
response or message — or an instruction, "Always close with" — and which says it
closes or ends with some calls to action must name the tail of `closing_order`,
in its order. It skips negated sentences, budgets for one topic, objects that
name no call to action, and subjects other than the response: a pack, a cell or
a drill turn ends with other things. Three eval expectations had contradicted
their skill's declaration unnoticed.

**A worked fit ledger is its own evidence map, projected.** `--only fit-ledger`
reads job-underwriter's worked dossier: the decision snapshot's ledger, one line
per Priority tier and its rows grouped by Fit, against the evidence-map table's
#, Priority, Fit and Confidence columns and against the JSON envelope's
`evidence_map`. Every row appears once, in enum order, each filed where the map
files it; a row below `direct` is named in its Requirement's own words; a
band in the snapshot sits beside one row and is that row's; and the envelope's
`decision.summary` holds no "N of M". The ledger was a sentence from v0.1 —
"five of seven material requirements are `direct`" over a map with four — and a
dossier whose ledger cannot be parsed fails rather than skips, so a revert to that
sentence is caught. What it does not read: any other prose about the map, in the
dossier or anywhere else, and the ledgers that runs write, which the eval
harness's own check reads instead.

**A skill's installed text quotes none of its own fixtures.** `--only answer-keys`
reads every double-quoted span of four words or more in a skill's `SKILL.md` body
and references, and fails one that appears in that skill's own eval prompts. A
clean room installs the references, so an example built from a fixture is an
answer key beside the model; three were found at once, none chosen. What it does
not read: unquoted prose, spans under four words, the frontmatter, `citations.md`,
and other skills' fixtures, since a room never installs two skills. A worked
example drawn from a fixture's domain without quoting it passes, which is why the
worked examples now sit in a domain no fixture uses.

**The ledger points; it does not restate.** Name the file and section that
changed (`evidence-conventions.md` §5), and cite rather than quote a source. A
ledger entry restating a rule becomes a second copy of it, and this ledger once
asserted a rule and its retraction four bullets apart because the rule changed
and the copy did not.

**The self-test runs in both directions.** Its baseline is the whole gate:
`ci/test_checks.py` used to run one group on the clean repo and then print "clean
repo passes", and a mutation of a group already failing proves nothing about the
mutation. Each mutation is a defect a check must refuse. Each must-pass case is
correct text in a form an earlier version refused, or for a new group a correct form its check must not refuse — a label that is this file's
own heading, a statute's §, stacked markers, a negated sentence — because a check
that refuses correct work teaches authors to distort prose or switch it off, and
that fails the self-test the same way an evasion does. Three reviews of these
checks found that each heuristic added to read more English opened as many holes
as it closed; they now read only forms they can read exactly, and the lists of
what they do not read above are the price of that.

## Structural rules

- Skills are dependency-free: nothing outside a skill's folder may be required
  at runtime. Agent tooling never leaks into skills/.
- conventions/ is canonical. Skills carry mirrors in references/ with a
  synced-from header; a mirror that drifts from canonical is a defect, and the
  fix flows canonical -> mirror, never the reverse.
- Every skill upholds the standalone invariant (interaction-grammar.md §1).
- Every skill folder carries its own LICENSE copy, so packaged .skill files
  and zips remain self-describing when they travel detached from the repo.
