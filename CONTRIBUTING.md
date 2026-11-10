# Contributing

Three rules protect this repository's structure while it is early; everything else is ordinary.

## Pull requests: collaborators and prior contributors only, for now

This is an early repository. The skills' output contracts, the shared
conventions and the eval harness still change from week to week, and every
change here is reviewed adversarially and measured on pinned runs before it
lands. A pull request from outside that loop would be written against a target
that moves under it, and would cost more to review than it saves. So for now,
pull requests are open only to the repository's collaborators and to prior
contributors (anyone with a commit on the default branch). A workflow,
`.github/workflows/pr-policy.yml`, closes any other with a comment pointing
here. Ideas, bug reports and failures you hit using a skill are welcome as
issues. This is revisited when the contracts settle, and at the latest before
any public release.

## Licensing

The repository is MIT-licensed for now (the root `LICENSE`). `conventions/` and
each skill folder carry their own copy of the same grant, so a packaged skill
travels with its license. A contribution is made under that grant. The one
planned exception is the future agent/ directory, below: when it exists it
will carry its own license, and files are not moved across that boundary in the
same change that modifies them.

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

## Fixtures model what users typically send

A standing rule, set by the owner. A fixture is written the way a typical user
writes the request, and what it expects is what serves that user. A test that
turns on a detail most users would not give, such as when they copied a page,
tests a hypothetical, and a skill tuned to pass it is tuned for the wrong case.
So a quick, reported check that pasted material is still current and genuine is
not a defect: a typical user does not say how fresh their material is.

## When an issue survives two iterations

A standing rule, set by the owner. An issue that two fix iterations have not
closed — each iteration a change made to close it, then reviewed or measured — is
not iterated a third time on its own. Work on it stops and it goes to the owner
as a decision, with its measurement: the rate, what each iteration changed, and
what each option would cost.

Modules shape up differently, so the owner decides case by case, among three
options:

- **A watch-out,** if the user can protect themselves by checking something: the
  issue is covered by that skill's watch-out, the one sentence every delivered
  output of the skill ends with (`conventions/output-discipline.md` rule 7). If
  the sentence does not already cover the issue, extend it — and keep it one
  sentence, because the slot holds one line and a list of cautions is read as
  none. The issue is added, with its rate and a link to its ledger entry, to the
  skill's "Why it's there" cell in the README's watch-out table — which CI does
  not read, so it is also updated by hand when an issue the cell explains is
  closed.
- **Another round,** with its own bar fixed before it runs.
- **Left open,** recorded with its rate.

An issue the user cannot protect themselves from — the skill does not fire at
all, say, so there is no output to check — can only be another round or left
open. Whatever the owner decides, the issue's entry in the README's Tracked-work
ledger records it as "Owner's decision after two iterations: …", with the
measurement. When most of those decisions are "a watch-out", say so to the owner:
the rule may then go back to adding the watch-out without asking.

Any two changes made to close an issue count, whatever their kind. For a
deterministic failure the rule above makes the second one a change of shape; for
an intermittent one, recording its rate is not an iteration.

A watch-out has one source, the `watch_out:` parameter in the skill's
`SKILL.md` — the whole line, label included — and a change to it is made there.
Its copies — the root README's watch-out table, each fixture's closing
expectation, any worked example that shows a response's last line — are never
edited on their own: `check_skills.py --only watch-out` fails until every copy
matches the parameter in the form `conventions/output-discipline.md` rule 7 gives
it, so the change reaches
them in the same commit. The README says all of this to users in plain words, under "Watch-outs:
what to double-check".

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

**A watch-out is one line, and every copy of it is exact.** `--only
watch-out` holds each skill's `watch_out` parameter to the label `**Watch-out:**`
and then one sentence of at most forty words, with no bracket, pipe or code span;
checks that `closing_order` ends with `watch-out` and that `output-discipline.md`
defines the slot; and compares every copy with the parameter character for
character — any line labelled a watch-out in the skill's own `SKILL.md`, README
and references, every fixture's expanded expectations (each must carry the line,
since a grader sees the fixture and not `SKILL.md`), and the root README's table,
one row per skill, in the form `output-discipline.md` rule 7 gives it. It also
fails the standing rule's heading going missing from this file, since the README
links to it, and a line labelled a warning anywhere a rule is stated or graded.
It does not read whether a sentence is plain, whether it names the defect the
ledger measured, or the README table's "Why it's there" column; that is review's.
A known limit: it does not read the prose that states the closing order either —
a sentence such as "nothing follows the questions" or "the questions close the
message", edited back into a `SKILL.md`, a reference or the convention, passes
every group. `--only parameters` reads only "closes/ends with" clauses, so those
statements are held by review.

**A worked fit ledger is its own evidence map, projected.** `--only fit-ledger`
reads job-underwriter's worked dossier with the rule functions in
`ci/ledger_rules.py`, which the eval harness calls on the output of runs, so the two
checks of one rule cannot disagree. The snapshot is read through its last bulleted
slot; the template's commentary after the slots is not read (in a run, the harness
reads the whole snapshot section). The ledger — one line per Priority tier, its rows
grouped by Fit, each Fit once per line — is read against the evidence-map table's #,
Requirement, Priority, Fit and Confidence columns and the JSON envelope's
`evidence_map`: every row once, in enum order, filed where the map files it, and a
row below `direct` named only in words its Requirement cell uses. A band beside a
row ID, backticked or not — R3 (`medium`), R3 (medium) — is that row's Confidence; a
band beside a register ID is a severity written like a band and fails, and so does
one attached to nothing. Everything between the ledger and the next slot is rule 2's
one sentence; a second sentence there fails. It must also take rule 2's list form,
each item up to a semicolon opening with its row IDs, a band beside them allowed,
then a dash (`ledger_rules.ledger_sentence_form`, which the harness records on runs
and gates nothing on). That sentence, the rest of the snapshot (the status line
included) and the envelope's `decision.summary` are read for set claims over the map
by one reader, `ledger_rules.set_claims` (through
`map_claim` and `after_ledger_claim`), here and in the harness. What it reads of
evidence-model.md's rule ("The row is the unit") and what it leaves to the grader
are stated once, in the comment above `Claim` in `ci/ledger_rules.py`; what is a
count, which words are map words, how far a count reaches, and when "N of M" or a
fraction counts rows, in the comment above `MAP_WORDS`. The **Hard gates:** slot is
required in every snapshot and parsed as rule 4 states it: its failed, unconfirmed
and met clauses are compared with the map's `hard_gate` rows, each failed and
unconfirmed row named in words its Requirement uses, and the closing clause with the
envelope's `candidate_constraints.status`; and every `hard_gate` row's fit must be
`direct`, `unclear` or `hard_gate_fail`, with `hard_gate_fail` on a `hard_gate` row
only (evidence-model.md, "A gate is met, not established, or failed"), whatever the
line says. Every `severity: x` beside a register ID is that entry's Severity, and
**Severe red flags:** names exactly the `severity: high` entries or says "none
found". There is one Research tier line, read with the harness's own pattern, its
L1 budget SKILL.md's and no count above its budget. And the quantifier lists in
evidence-model.md ("The row is the unit") are the one statement of the words: the
shared sets hold exactly them, list by list — the named-set words, the complements,
and the word scoped to the sentence after the ledger; risk-and-decision.md's rule 2
points to them and spells none of them; and every job-underwriter expectation that
speaks of quantifiers quotes each of their words, sorted as the rule sorts them —
each named-set word inside the expectation's sentence on the named-set words, each
complement inside its sentence on the complements, and the scoped word inside its
sentence about the sentence after the ledger and nowhere else.
The ledger was a sentence from v0.1 — "five of seven material requirements are
`direct`" over a map with four — and a dossier whose ledger cannot be parsed fails
rather than skips. What it does not read: whether the tally's numerators are true
(the target table records a status per target, not calls); a count or quantifier
beyond the reach `MAP_WORDS`'s comment gives ("both of them sit, in the end, below
`direct`" outside the sentence after the ledger), or about the map in words none of
these ("the hard gates fail"); what the comment above `Claim` leaves to the grader
— agreement with the map everywhere, and every set claim outside the snapshot and
the summary — which that comment states once; and the snapshots and summaries runs
write, which the harness reads with the same functions.

**A skill's installed text shares no run of words with its own fixtures.**
`--only answer-keys` reads each skill's `SKILL.md` body and references — the files a
run is told to open — and compares them with everything a clean room shows the
model of that skill's fixtures: every prompt, and every canned research page's
title and text. A conventions mirror is read in each skill that carries it, against
that skill's fixtures. A quoted span — in double, single or curly quotes, or a code
span of more than one word — fails when three of its content words in a row (stop
words dropped on both sides) are three in a row in a fixture; prose outside quotes
and code spans — fenced code included, so an unquoted value in a worked YAML row is
read — fails on six words in a row, stop words included. A snake_case identifier is
one word: a schema field a fixture repeats by contract is not six words of its
prose. A
clean room installs the references, so an example built from a fixture is an answer key beside the model:
three were found at once, none chosen, and the exact-quote check that followed
missed a near-quote, a single-quoted copy and two compressed ones. The windows were
set by running the check on the clean tree and reading every hit: at three content
words each quoted hit was fixture material, and unquoted prose had none at six.
Wording a fixture repeats by design — the shared contract's own phrases — is listed
in `ANSWER_KEY_CONTRACT` with its reason and masked; a phrase that is merely common
is a reason to rewrite the example, never to list it. The matcher is seeded with a
near-quote of each skill's first prompt and fails if it misses it. What it does not
read: a fixture's domain or situation in other words — the same shape of gap with
fewer than three content words in common passes, so a worked example's domain is
left to review (job-underwriter's worked dossier, like the other skills' worked
examples, sits in a grants-programme domain that no fixture uses); the README, `docs/`, the
frontmatter and `citations.md`; and other skills' fixtures, since a room never
installs two skills. Tuesday is the exception: a fixture run through it
installs every module's text, so its installed text is read against every
module's fixtures.

**The fixture fields the harness reads are what it assumes.** `--only fixtures`
reads every fixture through the harness's own functions in `evals/output_checks.py`
and `evals/research_server.py`, in every mode the fixture runs. A canary names its
`page` (required in a fixture with a canned mode), that page is exactly one of the
fixture's pages for the canary's target, and one of its spellings is in that page's
text — a canary whose page matches nothing is never asked for and passes every run.
What a canary may be is stated once, in `evals/README.md` ("What a canary may be").
A fixture that runs the quotes or traces check declares `candidate_text` as a list,
and each entry is in the prompt; one that runs the fit_ledger check declares
`candidate_constraints` as exactly "known" or "unknown". `research.declined`, where
present, is true or false; a fixture that sets it true does not also set
`zero_calls`, and its `research.declined_phrase` is in the prompt. A fixture with
research runs the `yes_names_page` check exactly when its skill's `SKILL.md` states
that every `yes` row names its pages (`evals/README.md`, "Deterministic checks"). Each
`research.user_links` entry is a URL that is no research page and no canary's page.
Every research target has `on_target_samples`, each aimed at the target in every
room the fixture runs; a target that accepts `n/a` or `skipped` has `hunt_samples`,
one of them aimed at it in each room where it accepts those, and no other target's
on-target sample is aimed at it there — by its terms in any room, or in a canned
room by a page the server returns for that sample — so a correct `n/a` is not failed
by a question about the process. At most one target declares `identity` (what it is
is stated in `evals/README.md`); its names are in the prompt and in no target's
terms, and some `research.stray_samples` query carries one, while every stray sample
is aimed at no target in any room the fixture runs. A fixture in which no correct
run sends a call (`zero_calls`, or `declined`) is not read for that last collision:
any call there fails `zero_calls` first. A `research.quick_check` lists declared
targets that accept `skipped` alone and names the prompt carries, sits beside no
`declined` and within the search budget, has no sample of its targets aimed at a
target outside them and passes no other target's sample as a quick check, and each
fixture file's `quick_check` clause allows `output_checks.QUICK_CHECK_CALLS` calls,
as `interaction-grammar.md` §4's quick-check sentence does. What it does not read:
whether a canary's spellings are figures, names or titles; whether the declined
phrase declines; and whether the samples are the queries runs actually send.

**Retired wordings stay retired.** `--only wording` reads every skill's `SKILL.md`,
README and references, conventions/, `evals/README.md`, and every clause,
expectation and expected output as the runner expands them. It fails "returned
something" and "every call was refused" without "or errored", the accounting labels
an errored call broke; "front door", Tuesday's old working name; the wordings this
round's rule changes retired — "only when the search budget was fully spent" in a
sentence that names neither L0 nor declining research, the sole ground for a no-call
`unavailable`; `user links read` counted with "refused ones included"; failed gate
rows named "plainly"; a missing hard-gates slot failing only "when the map has gate
rows"; and "years" within a sentence after "hard gate(s)", unless a negation governs
"hard gate" or "years" itself ("not a hard gate", "terms, never years") — the rule
that retired years from the list; a negation of anything else in the sentence ("hard
gates, never bridged, are … years") exempts
nothing (`SentenceRule` in `ci/check_skills.py` states the reading). It also
fails an expectation or clause that defines the yes/unavailable labels without
"returned a result" and "or errored"; an L0 definition — a paragraph
or list item naming L0, or one under a heading that does — that says "no network";
and, in mock-interview's personas.md, a story pre-mapped ("pre-map", "every … story
ends with") in a block that says nothing of a quote, or the loss of the line under
"The seven personas" that points to the quote-or-slot rule in question-rubric.md.
It reads these phrases, and for the budget and years wordings the sentence each
stands in (`SentenceRule` in `ci/check_skills.py`), and nothing else: a paraphrase
of a retired wording passes.

**Every declared enum has a column.** `--only columns` reads each skill's
`enum_columns` declaration beside `enum_fields`: it maps every declared enum to the
one table that renders it, as `field=file.md#Section/Column` — a reference file, a
`## ` section in it, and a column of the first worked table (a header row, then a
separator row) in that section. A declared enum with no mapping, a malformed
mapping, a file, section or worked table that is not there, a column that table
lacks, a mapping for an undeclared field, and a mapping into a mirror (a file with a
SYNCED FROM header) fail. A mirrored glossary defines the tokens and is never the
table a response renders: while any same-named header answered, the fit snapshot
could lose its Gap type column and pass on the glossary's. `qualifier_fields` and
`provenance_sections` are read in the same worked tables, outside the mirrors. What
it does not read: whether the cells hold only the enum's tokens.

**A skill meets Anthropic's authoring guidance, and keeps meeting it.** `--only
guidance` holds what the guidance asks of a shipped skill: a `## Contents` list
directly under the H1 of every reference file over 100 lines as shipped — a
mirror's synced-from header counted, so a canonical file near the limit carries
the list for its mirrors; a `SKILL.md` body under 500 lines and under 5,000
tokens, estimated at four characters a token; a description whose first word is a
third-person verb, read as a word ending in "s", where a word ending in "ss"
("Assess") is a bare imperative; and every file in `references/` linked from
`SKILL.md` as `references/<name>`, the path that resolves in the installed skill.
The frontmatter group holds the guidance's other frontmatter limits: only the six
keys the spec allows (claude.ai rejects any other), a description of at most 1,024
characters, no angle brackets, and no unquoted value a strict YAML parser misreads
(a `: ` or ` #` inside it, or a leading indicator), since Claude Code's lenient
reader takes what an upload refuses. Rationale and measurement history a `SKILL.md`
sheds to stay under the estimate go to that skill's `references/rationale.md`,
which is never required reading. What it does not read: whether a contents list
matches the file's headings, whether a description stays in the third person past
its first word, and whether a reference is linked at the step that needs it
rather than only in the index; review holds those.

**A clause is defined once and expanded once.** `--only evals` reads every evals.json
through `evals/fixture_clauses.py`, as the runner does: an expectation naming a
clause the file does not define, a clause nothing uses, and braces left in the
expanded text — a clause inside a clause, a name the loader cannot read — fail.
It reads each fixture's dates relative to the run at its `date_anchor`, as every
group does, and fails relative dates with no anchor, an anchor with none, and a
date reference the loader cannot read (`evals/README.md`, "Dates relative to the
run").

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

## Tuesday ships what was measured

Tuesday, `skills/tuesday/`, is a skill like the modules: its SKILL.md is
written by hand and its `references/` are generated from the modules
(`skills/tuesday/README.md` says how). It ships its SKILL.md, its `references/`
and its LICENSE, in every build and in the harness's install. Its README.md is
for maintainers and ships nowhere (`HUB_SHIPS` in `ci/sync.py`). Round 3
installed Tuesday as SKILL.md and `references/` alone; the LICENSE, the
modules' LICENSE byte for byte, is the one shipped file of Tuesday's it did not
hold. CI reads Tuesday in every per-skill group but a few, and
`HUB_EXEMPT` in `ci/check_skills.py` states each exemption's reason once; its
output prints them. Two groups hold what is particular to it.

`--only frontdoor` holds Tuesday to its sources and to its measurement.
`skills/tuesday/` holds SKILL.md, LICENSE, README.md and `references/`, and
nothing else; `references/` is one flat folder, exactly what `ci/sync.py`
generates. Every module has a playbook there and every file a playbook names is
there; Tuesday links no file that is not there, and the guidance group, which
reads it like every skill, holds the other direction. The modules Tuesday
routes to, read from its slash-command list and its routing table, are
`skills/` without it, and its description names each one. `MEASURED_FRONTDOOR`
records what round 3 measured as three hashes: Tuesday's SKILL.md, Tuesday with
its references, and every file the Claude Code builds ship, Tuesday's and each
module's, frontmatter, README and LICENSE included. So a change to any shipped
file of Tuesday or a module, or to a convention a module mirrors, fails until it
is measured, or until the constant is updated on purpose with the reason in the
ledger. The constant also holds the plugin's version, and an update to its
hashes moves the version: a user who installed the plugin keeps the copy they
have until its version changes. What it does not read: whether a routing row
or a link's read-when clause is right; the routing measurement and review hold
those.

`--only builds` holds the Claude Code builds, which `ci/package.py` writes beside
the `.skill` files. In `dist/claude-code/` and in the plugin's `skills/`, each
module's SKILL.md is its source with one line added inside the frontmatter,
`disable-model-invocation: true`, and Tuesday's is its source unchanged.
That line ships nowhere else: no file under `skills/`, and no `.skill` file, since
a claude.ai upload refuses the key. Tuesday's build, in both trees and in
`dist/tuesday.skill`, holds only the files it ships. The plugin's `skills/` is
`dist/claude-code/` file for file; the plugin manifest names the plugin
`tuesday` with a description and the version `MEASURED_FRONTDOOR` records; and
the marketplace file lists it, under the manifest's name, from the plugin's
folder. That every built file is current is the package group's. What it does
not read: whether Claude Code loads the plugin; `claude plugin validate` and a
session do.

## Structural rules

- Skills are dependency-free: nothing outside a skill's folder may be required
  at runtime. Agent tooling never leaks into skills/.
- conventions/ is canonical. Skills carry mirrors in references/ with a
  synced-from header; a mirror that drifts from canonical is a defect, and the
  fix flows canonical -> mirror, never the reverse. `python ci/sync.py` rewrites
  every mirror from its canonical file and Tuesday's references/ from the
  modules; `--check` reports what is out of date.
- Every skill upholds the standalone invariant (interaction-grammar.md §1).
- Every skill folder carries its own LICENSE copy, so packaged .skill files
  and zips remain self-describing when they travel detached from the repo.
