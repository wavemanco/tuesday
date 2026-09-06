# Coverage, gaps, and what this skill refused to write

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

`status` is one of exactly three values, one token per cell:

- **`already_evidenced`** — the current resume supports it as written. No row needed; say so.
- **`surfaced_by_edit`** — the evidence exists but is buried, mis-sectioned, or compressed away. Names the ledger row that fixes it.
- **`not_evidenced`** — the resume does not support it. Names the recovery move below.

The third value is the honest one and it must never be quietly absent. A coverage
map with no `not_evidenced` rows against a real JD is either a perfect match or a
map that stopped looking, and the second is far more common.

Two disciplines:

- **`already_evidenced` is a claim about the reader, not the writer.** The test is whether someone who has never met the candidate would find the requirement satisfied on one read — not whether the candidate knows it is true.
- **Never mark a requirement `surfaced_by_edit` on the strength of a plan to write the row.** The row exists first; the map points at it.

## Recovery, per gap

**`not_evidenced` with something to pull → the recall prompt.** The workhorse.
People forget what they have done until an example shaped like their own life
jogs it, so the examples must be specific to this JD and plausibly inside this
candidate's history.

```text
Requirement: [exact JD requirement or a concise paraphrase]
Importance: [must-have / important / preferred]

What your resume currently shows:
[what it does and does not establish — one or two sentences]

Why this matters here:
[what it costs on this application specifically]

Experience that may count:
- [JD-specific example 1]
- [JD-specific example 2]
- [JD-specific example 3]

Useful evidence to attach or link:
[specific artifact types — a spec, a dashboard, a launch note, a review, a repo]

Question:
[one focused question]

Answer in text, paste a voice transcript, attach a document, drop a link, or say skip.
```

**`not_evidenced` with nothing to pull → the named absence.** Say it plainly, in
one sentence, with what closing it would take: a project, a certification, a
scoped-down target. No cushioning it into vagueness, and no offering of a
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

- "Product management experience" — you have never held the title and the JD makes
  it a must-have. Adjacent work is in E1 and E3; the gap is named in the coverage
  map rather than papered over.
- "Owned the partner platform roadmap" — you coordinated on custom builds. Owning a
  roadmap is a different job and an interviewer will know within one question.
- "Partner integrations" — the posting's word is "partner"; yours is "client". You
  worked at the vendor. The word change would move which side of the table you sat
  on.
```

That last entry matters more than it looks. It is a single word, it is the
posting's own word, and it would have passed every review that was not looking
for it.
