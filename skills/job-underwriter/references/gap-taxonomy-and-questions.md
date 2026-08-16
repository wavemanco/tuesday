# Gap taxonomy and recovery questions

"Missing from the CV" is four different situations wearing one costume, and only one of them is a real capability problem. This file is how the skill tells them apart, and how it asks the questions that convert one into another. Vocabulary is an operative copy of `conventions/evidence-conventions.md` (canonical — it wins on any conflict).

## Fit status

Per material requirement, `fit_status` is one of: `direct`, `adjacent`, `unclear`, `absent`, `hard_gate_fail`. When fit is not `direct`, classify the gap:

| Gap type | Definition | Appropriate next action |
|---|---|---|
| `presentation` | Verified evidence exists; the CV doesn't communicate it in role-relevant terms | Propose a truthful repositioning, contingent on user approval |
| `discovery` | Evidence may exist; current inputs are inconclusive | Ask one targeted, example-rich question; suggest exact artifacts |
| `transferability` | No direct match, but credible adjacent work | Make the transferable case *and its limits*; consider a work sample |
| `capability` | No credible direct or adjacent evidence | Name a realistic closure path, or carry as material risk |
| `hard_gate` | Eligibility, credential, or constraint not met | Surface prominently; wording cannot solve it and no output may imply otherwise |

Two classification disciplines keep the taxonomy honest:

- **Down-classify claims, not people.** `capability` means *no credible evidence after looking* — it is a statement about the evidence, reached only after discovery and transferability have been genuinely explored. Reaching it on a first pass, from a CV alone, is almost always premature; `discovery` or `unclear` is the honest first-pass call.
- **Never up-classify to flatter.** Adjacent work asserted as direct experience is exactly the inflation the truthfulness core forbids. `adjacent` with the limits named reads weaker and interviews stronger.

## Recovery patterns, per gap type

Each gap type has a distinct recovery move. Using the wrong one — asking a question where a proposal is due, proposing wording where the gap is real — wastes the turn.

**`presentation` → the repositioning proposal.** Not a question; the evidence already exists. Show the current framing and the proposed truthful reframing side by side, source-cited, and mark it `resume_edits_pending_approval`. The proposal may reorganize, rename, and surface — it may never add a fact the evidence doesn't hold. Check scope words one by one against the source claim: the drift from "the team uses it" to "adopted org-wide" is a new claim, not a reframe, and it fails the truthfulness core however natural it sounds in product language.

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

- **At most three questions per turn** — and fewer when fewer could change anything. Zero is correct when the decision is already stable: a decidable case does not earn an interview.
- **Prefer questions that could move the decision status.** A question that only polishes an already-`direct` row loses to one that could resolve a must-have.
- **Never ask for what was already supplied, and never re-ask.** Silence and "skip" are answers: mark the gap unresolved (or `absent`, if the user says so) and proceed.
- **Research before asking.** Never ask the user what the public web knows.
- **Consent items ride, never drive.** The deep-research offer shares a message with real questions; it never costs its own round-trip.
- **Confidential work is answerable.** Offer the high-level path explicitly; record the answer with verifiability marked and confidence capped at `medium`.

## Response modes

Modes are prose offers in text hosts — "answer in text, paste a voice transcript, attach a document, drop a link, or say skip" — never bracketed pseudo-buttons, which promise interactivity a text host doesn't have. A pasted transcript is processed like any voice answer: extract the claims, run the confirmation card from `references/evidence-model.md`, and record as `user_confirmed_voice` once the user approves the extraction.

## Worked discovery prompts

Cross-functional delivery:

```text
Requirement: Lead cross-functional delivery across product, engineering, design, and go-to-market.
Importance: Must-have.

What I currently see:
Your CV establishes product-building work, but not which functions you coordinated, your decision authority, or launch ownership.

Why this matters:
This is a must-have; resolving it likely moves the decision from hold to conditional-go.

Experience that may count:
- Taking a product, feature, experiment, or client project from idea to release.
- Coordinating an engineer, designer, contractor, customer, or marketing effort — titles don't matter, the coordination does.
- Setting priorities or resolving a product-versus-technical trade-off others accepted.

Useful evidence to attach or link:
A launch plan, roadmap, project board export, portfolio write-up, or product brief.

Question:
Is there a project where you personally coordinated two or more functions to ship something? What did you own, who was involved, and what happened?

Answer in text, paste a voice transcript, attach a document, drop a link, or say skip.
```

Production AI/LLM experience:

```text
Requirement: Production experience with LLM applications, including evaluation and monitoring.
Importance: Must-have.

What I currently see:
Your CV mentions AI-related work, but does not establish deployment to real users, evaluation, monitoring, or measurable outcomes.

Why this matters:
The distance between "prototype" and "production" is exactly what interviews for this role will probe; knowing which one is true decides the positioning.

Experience that may count:
- Designing prompts, agent workflows, RAG systems, evals, or guardrails that others used.
- Managing quality, latency, reliability, or cost trade-offs on a live system.
- Running a pilot with real users, measuring outputs, handling failure modes.

Useful evidence to attach or link:
A repo, README, architecture diagram, eval sheet, demo, or launch note.

Question:
Which parts of an AI system have you personally owned, did it reach users beyond a private prototype, and how did you know whether it worked?

Answer in text, paste a voice transcript, attach a document, drop a link, or say skip.
```
