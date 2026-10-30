# Gap taxonomy and recovery questions

## Contents

- Fit status and gap type
- Recovery patterns, per gap type
  - The reframing audit
- Selecting the next questions
- Response modes
- Worked discovery prompts

How this skill tells four situations apart and asks the questions that convert one into another. The vocabulary it uses is defined in `references/evidence-conventions.md`, the suite's canonical file mirrored verbatim into this skill; what follows is this skill's own method for applying it.

## Fit status and gap type

Per material requirement, `fit_status` is one of `direct`, `adjacent`, `unclear`,
`absent`, `hard_gate_fail`; when fit is not `direct`, the gap is classified as
`presentation`, `discovery`, `transferability`, `capability`, or `hard_gate`.

Both sets, and the definition of each gap type with its appropriate next action,
live in `references/evidence-conventions.md` §3 — the suite's canonical
vocabulary, mirrored verbatim into this skill. Read them there rather than from
memory. The taxonomy earns its complexity because "missing from the CV" is four
different situations wearing one costume, and only one of them is a real
capability problem.

Two classification disciplines keep the taxonomy honest:

- **Down-classify claims, not people.** `capability` means *no credible evidence after looking* — it is a statement about the evidence, reached only after discovery and transferability have been genuinely explored. Reaching it on a first pass, from a CV alone, is almost always premature; `discovery` or `unclear` is the honest first-pass call.
- **Never up-classify to flatter.** Adjacent work asserted as direct experience is exactly the inflation the truthfulness core forbids. `adjacent` with the limits named reads weaker and interviews stronger.

## Recovery patterns, per gap type

Each gap type has a distinct recovery move. Using the wrong one — asking a question where a proposal is due, proposing wording where the gap is real — wastes the turn.

**`presentation` → the repositioning proposal.** Not a question; the evidence already exists. Show the current framing and the proposed truthful reframing side by side, source-cited, and mark it `resume_edits_pending_approval`. The proposal may reorganize, rename, and surface — it may never add a fact the evidence doesn't hold.

Run the reframing audit on the proposal before showing it.
### The reframing audit

Read `references/reframing-audit.md` — the suite's canonical audit, mirrored
verbatim into this skill — and run it over the proposal before showing it. Six
axes and five disciplines, covering every word proposed for the candidate to say,
write, or send: resume bullets, positioning advice, outreach phrasing, interview
framing. It is canonical rather than local because resume-tailor's whole output is
proposed language and job-underwriter's is partly so; one copy cannot drift from
the other if there is only one.

**`discovery` → the recall prompt.** The workhorse. Structure every important discovery prompt like this:

```text
Requirement: [exact JD requirement or a concise paraphrase]
Importance: [hard gate / must-have / important / preferred]

What I currently see:
[what the CV and existing evidence do and do not establish — one or two sentences]

Why this matters:
[how it affects eligibility, the decision, or application strategy]

Experience that may count:
- [JD-specific example 1]
- [JD-specific example 2]
- [JD-specific example 3]

Useful evidence to attach or link:
[specific artifact types: a launch plan, repo, review, deck, dashboard screenshot, brief]

Question:
[one focused question]

Answer in text, paste a voice transcript, attach a document, drop a link, or say skip.
```

The "experience that may count" list is what makes recall work — people forget what they've done until an example shaped like their life jogs it. Make the examples specific to this JD and plausibly within this candidate's history, not generic career categories.

**`transferability` → the bridge case.** State three things together, always: the adjacent evidence (what genuinely carries over), the limit (what the adjacent work did *not* exercise), and the strengthener (the work sample, artifact, or framing that would narrow the limit). A bridge with no stated limit is inflation wearing a suit.

**`capability` → the closure path.** Say it plainly, without cushioning it into vagueness: no credible direct or adjacent evidence exists. Then either name a realistic closure path (a course, a project, a scoped-down target role) or carry it as a material risk in the decision. No question, unless the user signals the classification might be wrong — then it's `discovery` again.

**`hard_gate` → the surfacing.** A plain statement in the decision snapshot. Ask a question only when the gate itself is genuinely uncertain ("the JD requires work authorization — what's your status?"), never as a workaround hunt.

## Selecting the next questions

Rank every candidate question:

```text
priority = requirement_importance
         × uncertainty
         × expected_evidence_recovery_probability
         × decision_impact
         ÷ user_effort
```

Operational rules:

- **At most three questions per turn, counted across the whole message** — and fewer when fewer could change anything. Zero is correct when the decision is already stable: a decidable case does not earn an interview. The budget counts every question put to the user, wherever it sits. Recall-prompt rows in the gap queue carry no questions: the question each row implies is asked once, in the closing block, tagged to its row, and those make up the three. A queue that also carried its own questions would make a five-question turn out of two rows and a closing block of three, and it would put questions mid-message, which this skill's `closing_order` rules out.
- **Prefer questions that could move the decision status.** A question that only polishes an already-`direct` row loses to one that could resolve a must-have.
- **Never ask for what was already supplied, and never re-ask.** Silence and "skip" are answers: mark the gap unresolved (or `absent`, if the user says so) and proceed.
- **Research before asking.** Never ask the user what the public web knows.
- **Consent items ride, never drive.** The deep-research offer shares a message with real questions; it never costs its own round-trip.
- **Confidential work is answerable.** Offer the high-level path explicitly; record the answer with verifiability marked and confidence capped at `medium`.

## Response modes

Modes are prose offers in text hosts — "answer in text, paste a voice transcript, attach a document, drop a link, or say skip" — never bracketed pseudo-buttons, which promise interactivity a text host doesn't have. A pasted transcript is processed like any voice answer: extract the claims, run the confirmation card from `references/evidence-model.md`, and record as `user_confirmed_voice` once the user approves the extraction.

## Worked discovery prompts

A gap produces **two** things in two places, and keeping them apart is the whole
discipline: a **row** in the gap recovery queue, and a **question** in the closing
block. Both are rendered from the same envelope entry. They are split because a
queue that carried its own `Question:` line put questions fourth of nine sections
— failing `closing_order` in eight graded runs of fourteen — and created a second
question site in a message whose budget is counted across the whole message.

Worked, for a must-have the CV leaves unresolved:

**The row** — everything the reader needs to understand the gap:

| # | Gap (req) | Type | What I currently see | Why it matters | Experience that may count | Useful evidence | Provenance |
|---|---|---|---|---|---|---|---|
| G1 | Joint working with other funders (R2, must_have) | discovery | The CV establishes grant-making work, but not which partner organizations were involved, what decision authority was held, or who owned a joint call's launch | A must-have; resolving it likely moves the decision from `hold_pending_answers` to `conditional_go` | Running a call co-funded with another trust or a local council; bringing a funder, a council and community groups to one set of criteria — titles do not matter, the brokering does; agreeing a funding split or an eligibility rule the partners accepted | A partnership agreement, a joint-call timeline, a panel paper, or a programme brief | `[grounded]` CV silence on partnership scope; `[inferred]` that resolving it moves the status |

**The closing question** — in the closing block, tagged to its row, with response
modes as prose:

```text
G1 — Is there a fund or a round where you personally brought two or more
organizations to one decision? What did you own, who was involved, and what happened?
Answer in text, paste a voice transcript, attach a document, drop a link, or say skip.
```

A second, for a gap where the distinction itself is the finding:

| # | Gap (req) | Type | What I currently see | Why it matters | Experience that may count | Useful evidence | Provenance |
|---|---|---|---|---|---|---|---|
| G2 | Production LLM experience (R3, must_have) | discovery | The CV mentions AI-related work but does not establish deployment to real users, evaluation, monitoring, or measurable outcomes | The distance between "prototype" and "production" is what interviews for this role probe, so which one is true decides the positioning | Designing prompts, agent workflows, RAG systems, evals or guardrails others used; managing quality, latency, reliability or cost trade-offs on a live system; running a pilot with real users, measuring outputs, handling failure modes | A repo, README, architecture diagram, eval sheet, demo, or launch note | `[grounded]` CV mentions AI work without deployment detail; `[generic]` that this role family probes the prototype-production line |

```text
G2 — Which parts of an AI system have you personally owned, did it reach users
beyond a private prototype, and how did you know whether it worked?
Answer in text, paste a voice transcript, attach a document, drop a link, or say skip.
```

Where G2's is the last question, the response ends one line later — the watch-out
line, `closing_order`'s last item, copied exactly from SKILL.md:

```text
Answer in text, paste a voice transcript, attach a document, drop a link, or say skip.

**Watch-out:** A summary line here can contradict the evidence table — before you act on a count, an "only" or an all-clear, check it against the table's rows.
```

Note what the `Provenance` cell does in both rows. "Why it matters" is where this
section's world-claims live — a claim about what interviews probe, or about what
would move a decision — and they read as findings when they are patterns. Two
labels in one cell is correct here and is not a compound enum value: the cell is
free text describing a row with more than one derived claim in it.
