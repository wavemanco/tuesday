<!-- SYNCED FROM: conventions/output-discipline.md
     Canonical wins on conflict. Everything below this comment block is a
     verbatim copy of the canonical file — do not edit it here. Fixes flow
     canonical -> mirror, never the reverse; a mirror that drifts is a defect.
     A byte check strips this header and compares the remainder to canonical. -->

# Output discipline

Canonical for every Tuesday skill. Skills carry a mirror of this file in their
`references/` with a synced-from header; this copy wins on conflict.

Five rules about the *shape* of a delivered response. Every one was learned from a
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
be read and where nothing downstream tries to parse it. Where a row genuinely
holds two claims of different strength, split it into **two rows**, each with its
own single value — the split is legitimate and the slash is not.

**Parameter: `enum_fields`** — which of the skill's fields are enums. Their token
sets are defined wherever that skill defines its vocabulary.

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
