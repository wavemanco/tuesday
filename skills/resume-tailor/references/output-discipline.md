<!-- SYNCED FROM: conventions/output-discipline.md
     Canonical wins on conflict. Everything below this comment block is a
     verbatim copy of the canonical file — do not edit it here. Fixes flow
     canonical -> mirror, never the reverse; a mirror that drifts is a defect.
     A byte check strips this header and compares the remainder to canonical. -->
# Output discipline

Canonical for every Tuesday skill. Skills carry a mirror of this file in their
`references/` with a synced-from header; this copy wins on conflict.

Six rules about the *shape* of a delivered response. Every one was learned from a
measured defect in a clean-room run, and three of them were fixed twice in
different skills because nothing carried them across — the question budget in two
skills weeks apart, the enum cell in three separate files. That is what this file
is for.

## How to read this file

Each rule has an **invariant** and, where variation is legitimate, a
**parameter**. The invariant is canonical and absolute. The parameter is declared
by each skill in its own `SKILL.md`, under a heading of exactly
`## Output discipline`, one line per parameter:

```text
## Output discipline

question_budget: 3
enum_fields: priority, fit_status, confidence, gap_type
closing_order: dossier offer, upgrade menu, questions
sibling_mentions: 1
```

The split is not a compromise, it is the seam the defects revealed. The half that
kept failing was never the number — both skills already said "at most three"; what
broke was that a `Question:` line inside a template did not feel like it counted.
The counting rule is durable and shared; the count is a design decision belonging
to the skill that makes it.

**A skill declares every parameter this file names, including when its value
matches every sibling's.** A missing declaration is a visibly empty slot, and that
is the point: a fourth skill must not inherit a default it never considered. CI
fails a skill that omits one.

Some rules take no parameter. Those are marked **absolute** and admit no variation
— they describe a collision or a contradiction rather than a preference.

## 1. The question budget is counted across the whole message

**Invariant.** Every question put to the user counts, wherever it sits: inside a
recall prompt, inside a template, inside a worked example the user is meant to
answer, in a closing block. A `Question:` line does not become free by arriving
inside a structure.

Three recall prompts plus a closing block of two is a five-question turn, and it
reads as an interrogation however neatly it is sectioned. Either the embedded
prompts *are* the budget or the closing block is — never both.

**Parameter: `question_budget`** — the maximum for one turn. Fewer is always
allowed and often right; zero is correct when nothing asked could change anything.

## 2. Enum cells hold exactly one token

**Invariant.** A field whose values come from a fixed vocabulary holds one token
from that vocabulary and nothing else: no slash, no hyphenated pair, no
parenthetical, no qualifying clause. `low–medium`, `none/low`, `split`, `mixed`,
`discovery (sales piece)` and `surfaced_by_edit (partial — see G2)` have all been
written into such cells across this suite. Each is a different way of declining to
choose — two answers, or a qualifier smuggled into a slot with room for one.

The qualifier is not unwelcome. It belongs in a neighbouring column where it can
be read and where nothing downstream tries to parse it — **and that column has to
exist in the shape the writer is actually filling, not only in the spec.**
job-underwriter's row spec has declared a `reasoning` field since v0.1 and its
JSON envelope emits it; the markdown table the model writes omitted the column for
just as long, and `none/low` went into the `Confidence` cell next to it. A rule
that says "put the qualifier in X" is inert wherever X is not a cell the writer is
already filling: they have the nuance, find no home for it, and use the nearest
cell that will hold text. Before shipping a table, check that every field the
rules name as a destination has a column in it. Where a row genuinely
holds two claims of different strength, split it into **two rows**, each with its
own single value — the split is legitimate and the slash is not.

**Parameter: `enum_fields`** — which of the skill's fields are enums. Their token
sets are defined wherever that skill defines its vocabulary — and **every declared
enum needs a column to live in.** A field declared an enum with nowhere specified
to appear gets invented at write time, and an invented column arrives with no
token set: `low-medium` and `[grounded, partial]` are what that looks like. The
declaration and the output shape have to agree, or the parameter is a promise
about a cell that does not exist. So each skill declares, beside `enum_fields`,
the column each enum lives in — `enum_columns: confidence=Confidence, …`, one
explicit mapping per declared enum, to a header of a worked table in its
references — and CI fails a declared enum with no mapping, a mapping to no such
column, or a mapping for an undeclared field (`CONTRIBUTING.md`).

**Parameter: `qualifier_fields`** — the free-text columns a qualifier goes to when
it will not fit an enum cell. Every field named here must exist as a column in the
skill's worked template, and CI checks that it does: this is the rule above turned
into a mechanism, because "put it in `reasoning`" was true, documented, and
pointing at nothing for three skill versions. `none` is a legitimate value and
means the skill has no such column — visibly, so that the next person to add an
enum to it can see what they are choosing.

## 3. Square brackets are reserved for provenance labels — **absolute**

`[grounded]`, `[inferred]` and `[generic]` are the notation a reader depends on to
tell evidence from inference. No other notation may use square brackets: not `[x]`
for an n+x offer, not `[TODO]`, not `[optional]`. A reader who has learned to scan
for brackets must not find something else there.

No parameter. This is a collision, not a preference.

## 4. The calls to action close the message

**Invariant.** The sections a user acts on next are the last thing they meet, and
nothing follows them — no recap, no summary, no closing restatement, no
pleasantry.

The pull is to write one more sentence tying it together. That sentence is a
second summary of an analysis that already opened with one, and two summaries of
the same analysis can only agree by luck — the reader will trust whichever they
read last. Whatever leads the response is the summary; the response ends without
restating itself.

**Parameter: `closing_order`** — which sections are the calls to action, in order.

## 5. A sibling skill is named, not lobbied for

**Invariant.** Where a request touches a sibling skill's territory, name the
sibling and move on. A mention in the prose and another inside a closing question
is twice, and the second one is lobbying rather than informing — it spends the
user's attention on a skill they did not ask for.

**Parameter: `sibling_mentions`** — the maximum per message.

## 6. A claim about the world lives in a row, not in prose

**Invariant.** Free prose in a delivered output asserts nothing about the world.
It may quote a source, and it may read the analysis the reader can already see —
a line naming which rows of the map are `direct` is a reading, and deleting the
analysis deletes the sentence. A reading names what it reads: this example used
to be "five of seven requirements are `direct`", copied from a worked dossier
whose map had four, and a count is the one kind of reading that can be wrong
while looking finished. Anything that would still assert something with the analysis
gone is a world-claim: about the employer, the market, the candidate's history, or
how hiring works. Those live in a row, in a structure with a Provenance cell.

Four prose rules failed at this — three before the first table column, a fourth in the section still written as
prose — before it was written as a shape, and they failed
in a way worth naming: **a writer who knows where a claim came from cannot see the
sentence that fails to say so.** The label is missing from a sentence that reads
perfectly. Nothing about proofreading catches it, which is why the fourth rule did
no better than the first. An empty cell is visible; an absent suffix is not.

The corollary is the useful half. A world-claim with no row to sit in is not a
claim needing a label — it is a claim needing deletion. "Small companies of this
size routinely have thin public footprints" earns a register entry with a
`[generic]` label, or it earns nothing; what it must not do is sit in a paragraph
reading as a finding about this employer.

**Parameter: `provenance_sections`** — the sections whose tables carry a
Provenance column, named exactly as their `## ` heading reads and therefore
**containing no comma**, since the list separator is one. Every section named
must have that column in the skill's worked template, and CI checks it. This exists because the project ledger claimed for
weeks that a third table carried one when it never had, and the claim was believed
until a grader pointed at exactly that table's cells. A rule that names its own
coverage can be checked against the shape; a rule that says "label your claims"
cannot.

A parameter was drafted here and withdrawn: `entity_rows`, naming tables whose
every row was about the candidate or the employer, so that CI could reject a
`[generic]` cell in them. It shipped for exactly one commit and was wrong.
The skill owning the evidence map requires `[generic]` in a row's Provenance cell
whenever its Reasoning reaches past the row — "enterprise SE roles usually touch
pre-sales" — and names the pull to write `[inferred]` instead as the thing to
resist. The check would have rejected that row, and three worked examples besides.

**A check that rejects correct work is worse than no check.** The honest position
is the one in `evidence-conventions.md` §5: that rule is gradeable rather than
mechanical, and it says so, instead of shipping a mechanism that encodes a wrong
version of it. A suite with this many real checks can afford to name the gap.
