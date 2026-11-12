# Coverage, gaps, and what this skill refused to write

## Contents

- The coverage map
- Recovery per gap
- The confirmation card
- The prohibited-claims list

The ledger says what the resume *can* be made to say. This file covers the other
half — what the JD asks for that the resume does not support, and what to do about
each one. It is the half a tailoring tool normally skips, because naming a gap
looks like failing at the task.

It is the opposite. A candidate who knows which requirement their resume cannot
carry can decide to answer a recall prompt, attach an artifact, or stop applying —
and a candidate who is handed a resume that appears to cover everything walks into
an interview holding a document they cannot defend.

## The coverage map

One row per material requirement. A requirement is material when it plausibly
affects whether the resume gets read: every must-have, every important
requirement, and any preferred one the candidate could genuinely differentiate on.
Boilerplate ("self-starter", "fast-paced environment") is not material.

| # | Requirement | Priority | Status | Where it lands | Provenance |
|---|---|---|---|---|---|

`status` is one of exactly three values, one token per cell — no parenthetical, no slash, no qualifying clause. `surfaced_by_edit (partial — see G2)` and `not_evidenced (adjacent work exists)` are not statuses; they are a status plus the nuance that belongs in the *Where it lands* column, where it can be read without breaking anything that parses the status.

The three values:

- **`already_evidenced`** — the current resume supports it as written. No row needed; say so.
- **`surfaced_by_edit`** — the evidence exists but is buried, mis-sectioned, or compressed away. Names the ledger row that fixes it.
- **`not_evidenced`** — the resume does not support it. Names the recovery move below.

The third value is the honest one and it must never be quietly absent. A coverage
map with no `not_evidenced` rows against a real JD is either a perfect match or a
map that stopped looking, and the second is far more common.

Two disciplines:

- **`already_evidenced` is a claim about the reader, not the writer.** The test is whether someone who has never met the candidate would find the requirement satisfied on one read — not whether the candidate knows it is true.
- **Never mark a requirement `surfaced_by_edit` on the strength of a plan to write the row.** The row exists first; the map points at it.

## Recovery per gap

**`not_evidenced` with something to pull → the recall prompt.** The workhorse.
People forget what they have done until an example shaped like their own life
jogs it, so the examples must be specific to this JD and plausibly inside this
candidate's history.

A recall prompt produces **two** things in two places: a **row** here, and a
**question** in the closing block. They are split because a prompt that carried
its own `Question:` line put questions in the middle of the message *and* gave
the message a second question site — and the budget is counted across the whole
message, so three recall prompts plus a closing block of three is a six-question
turn however neatly it is sectioned. Measured, that is this skill's largest
recurring failure: 50% of graded runs on one fixture and 60% on another, stable
across three independent run-sets, every one of them counting embedded
`Question:` lines against the closing block.

| # | Requirement | Priority | What your resume currently shows | Why it matters here | Experience that may count | Useful evidence | Provenance |
|---|---|---|---|---|---|---|---|
| C1 | [exact JD requirement or a concise paraphrase] | must-have | [what it does and does not establish, in one or two sentences] | [what it costs on this application specifically] | [JD-specific example]; [JD-specific example]; [JD-specific example] | [a spec, a dashboard, a launch note, a review, a repo] | `[grounded]` what the resume does and does not say; `[generic]` what this costs on applications of this kind |

The question each row implies is asked once, in the closing block, tagged to its
row and carrying the response modes:

```text
C1 — [one focused question]
Answer in text, paste a voice transcript, attach a document, drop a link, or say skip.

**Watch-out:** The words I quote as yours beside each edit can differ slightly from what you wrote — before you approve a line or send the resume, check that quote and the new line against what you actually wrote.
```

The last line is the watch-out, `closing_order`'s last item, copied exactly from
SKILL.md; nothing follows it.

`Why it matters here` is where this section's world-claims live — what a
requirement costs on this application, what a screener does with it — so the row
carries a Provenance cell and those claims get labeled where they are made.

**`not_evidenced` with nothing to pull → the named absence.** Two parts, always,
and the second is the one that gets dropped. Say the gap plainly in one sentence —
then say what closing it would take: a specific project, a certification, six
months on a particular kind of work, a scoped-down target role. "You have never
run a capital-grants programme, and it is listed as a plus rather than a requirement" is half an
answer; it tells the candidate where they stand and nothing about what to do,
which is the half they came for. An absence with no closing path is an
unfinished row even when the honest closing path is "not worth closing for this
role" — say that, and say why. No cushioning it into vagueness, and no offering of a
"technically true" phrasing that gestures at the requirement without meeting it —
that phrasing is the thing this skill exists not to write.

**Never a third option.** There is no path where a `not_evidenced` requirement
gets a hedged line in the ledger anyway. If it were writable, it would not be
`not_evidenced`.

## The confirmation card

When a recall prompt is answered — text, transcript, attachment, or link —
extract before you write a row.

```text
What I heard: [claim, in one sentence]
Ownership: [what was theirs vs. the team's]
Scope: [team / users / revenue / stakes — whatever was stated]
When: [period, if stated]
Outcome: [result or metric, if stated]
Artifact: [anything inspectable that was offered]
Missing for a resume line: [the one or two specifics a bullet would need]

Right, or should I correct something?
```

Only after the candidate confirms does a ledger row get written from it, and the
row's trace cell quotes *their answer*, not the extraction. A confirmed answer is
`user_confirmed_text` or `user_confirmed_voice` and may carry `[grounded]`; an
unconfirmed one may not enter the ledger at all.

## The prohibited-claims list

Carried in every delivery, not only when something was refused. It holds:

- **Claims the JD invites that the evidence cannot support** — the ones a less careful tool would have written. Naming them is what makes the refusal visible; otherwise the candidate cannot tell the difference between a skill that found nothing to inflate and a skill that inflated nothing.
- **Rejected rows**, with the candidate's reason, so no later turn re-derives them.
- **A dossier's `evidence_state.rejected_inferences`**, where one is present — inferences the underwriter already tested and the candidate already corrected.
- **Anything an answered recall prompt failed to confirm.** A prompt that came back "I don't think I ever did that" closes the requirement; it does not soften it.

```text
Not written, and why:

- "Programme management experience" — you have never held the title and the JD makes
  it a must-have. Adjacent work is in E1 and E3; the gap is named in the coverage
  map rather than papered over.
- "Owned the grants pipeline" — you ran one round of it. Owning a pipeline is a
  different job and an interviewer will know within one question.
- "Partnered with community groups" — the posting's word is "partner"; yours is
  "coordinated". You administered their awards, and the word change would move
  which side of the table you sat on.
```

That last entry matters more than it looks. It is a single word, it is the
posting's own word, and it would have passed every review that was not looking
for it.
