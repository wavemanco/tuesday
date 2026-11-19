---
name: mock-interview
description: Generates a personalized mock-interview prep pack — persona-categorized question banks with grounded answer guidance and rationale, a fit-gap map, company-values alignment, reverse questions, and optional live drill sessions where Claude plays the interviewer. Use this whenever someone is preparing for a job interview, even if they don't say "mock interview" — triggers include "prep me for my interview", "interview questions for this role", "help me practice for my interview at X", "how should I answer questions about my background", an uploaded job description and/or CV in an interview context, or any mention of an upcoming recruiter screen, hiring-manager round, panel, or final round. Also use when tailoring prep to a specific interviewer or company. Candidate-side preparation only — not for employers screening candidates, and not for deciding whether to apply or whether a role is worth pursuing (that is evaluation, not rehearsal).
---

# Mock Interview

Build a prep pack a candidate can actually rehearse from. Two axes organize everything: **personas** describe how the interview will feel (who is asking, in what style), and **question types** describe what is being scored. Every question in the pack carries answer guidance grounded in the candidate's real material plus a rationale explaining why it's included and why it's categorized that way.

Everything in the pack is either traceable to a provided document, traceable to research, or explicitly labeled as generic.

**Started by its own command, `/mock-interview`, this skill keeps the turn:** `references/interaction-grammar.md` §6 says what that rules out — read it before reaching for any other skill.

## Before sending

Copy this list and check the response against it. Each item points to its rule and restates none; rules 1, 5 and 7 are in `references/output-discipline.md`.

```text
1. A complete pack in the same message as any question (Step 1)
2. The pack's sections per the skeleton and conditionality table (Step 4)
3. The saved file stops at the upgrade menu; nothing of the message is in it (Step 4)
4. Questions within question_budget, counted across the message (rule 1)
5. The closing run in closing_order (Output discipline)
6. Watch-out line last in the message, exact, never in the pack file (rule 7)
7. Sibling named at most sibling_mentions times (rule 5)
```

## Workflow

### Step 0 — Intake and classification

Inventory every provided input against the contract below. Extract before you ask: seniority and team from an interviewer profile, company and level from a JD, round type from phrases like "final round" or "chat with the hiring manager".

Three special cases:

- **`tuesday-dossier.md` in context or uploads.** Read `references/dossier-handoff.md` (its fields are `references/dossier-schema.md`'s) and consume it: `handoff_to_mock_interview` carries verified evidence, allowed strategies per weak area, the objection worth the deepest rehearsal, risks and employer questions for the reverse bank, and absolute `prohibited_claims`; `role_profile` satisfies the JD tier. A dossier sharpens the pack — it never gates it, and a pack built without one is still a complete pack.
- **Government ID.** If an upload is or contains a passport, license, or ID number, don't use it, tell the user it isn't needed for interview prep, and proceed without it. Check content, not filename.
- **Personality / working-style assessments.** Accept if offered; never solicit one. They feed only the delivery-coaching section (Step 3) under the guardrails below.

### Step 1 — Elicit only what shapes the skeleton, and never before delivering

**A clarifying message never travels alone.** Whatever is missing, build a complete pack from what is available and deliver it in the same message as the questions: state in one line the assumption it was built on, and frame each question as what would restructure it. Use the degradation ladder below rather than waiting. Delivering does not retire the questions either — whatever is missing from (a) to (d) is still asked, in that same message, within the bounds the next two paragraphs set.

Ask at most three questions, covering only what's missing from: (a) **round type and relationship to the interviewer(s)** — manager, peer, skip-level, cross-functional, recruiter — folding in any recruiter/HR guidance in the same breath: stated focus areas, pre-declared deliverables (a POV, a presentation, a take-home), process details; (b) **JD and/or CV** if absent, with an explicit offer to proceed without — a dossier's `role_profile` and `verified_candidate_evidence` satisfy these tiers, so with one in hand neither is asked for and both drop to upgrade-menu lines; (c) **research depth consent** (Step 2); (d) **the gates the material says nothing about** — one question naming each such gate row of the fit snapshot, however many there are. It is the one question `references/evidence-conventions.md` §3 allows a gate, asked here because the snapshot's gate rows ask nothing (the routing rule in `references/output-template.md`).

The consent item rides along; it never drives. If (a), (b) and (d) are already satisfied, ask nothing — generate at the default research tier and place the deep-research offer in the upgrade menu instead. Where (a), (b) and (d) are all missing, the consent item is the one that gives way, to the upgrade menu the same way.

Never ask the user what the web knows; ask nothing outside (a) to (d).

If the user declines or doesn't answer, proceed down the degradation ladder. Never re-ask.

### Step 2 — Research at the consented tier

Read `references/research-checklist.md`, `references/interaction-grammar.md` §4 for the tier definitions and the target accounting it applies, and the accounting's worked table in `references/output-template.md`. Three tiers: **L0** (provided documents only — no search and no fetch of the skill's choosing; a link the user gave you to read is a provided document, read when the host can fetch it and named on the tally line, and a host that cannot fetch says so and uses only what was pasted), **L1** (default: at most 6 searches and 2 page fetches, spent only where a result could change the pack — official values, documented loop structure, one recent-strategy sweep, interviewer public footprint if named, a representative JD when none was supplied), **L2** (deep research: four further targets — strategy brief, interviewer talks and writing, role-family loop reports, recent org context — at most 6 further searches and 2 further fetches, offered once, with its caps and time cost stated, and run only on consent).

Company values, loop structure, and current strategy must come from research or provided docs, not from model memory.

### Step 3 — Synthesize

Read `references/personas.md` and `references/question-rubric.md` before writing any question, and `references/reframing-audit.md` before writing any guidance cell. The rubric applies `references/evidence-conventions.md` §2, §4 and §5 and `references/output-discipline.md` rule 1; with a dossier in hand, rule 2 of `references/dossier-handoff.md` too. Build in this order:

1. **Fit snapshot** — JD requirement × the candidate's evidence, quoted verbatim × gap-and-bridge language. The quotes are the pool everything after this draws on: whatever the pack later says about the candidate's past is one of these sentences, a plain acknowledgment sourced as `references/question-rubric.md` allows, or an answer slot — the pack's own observation that the material does not show something is analysis, not words for the candidate, and the rule, surface by surface, is in the rubric. Each row's gap type follows the routing rule under the worked table in `references/output-template.md`. The gaps found here become the Skeptic and Pressure banks' best material. With a dossier in hand, the underwriter's `evidence_map` supplies the grading — its confidence bands and gap types are the vocabulary this skill uses too, per the mirror in `references/evidence-conventions.md` — and its evidence quotes supply the cells, never its restated claims.
2. **Prohibited claims** — the claims this pack will not coach, and why, built here so the banks are written against them. With a dossier, `prohibited_claims` arrives from the underwriter and binds every guidance cell. **Without one, build it locally** from the fit snapshot — the claims a candidate reaches for under pressure, each entry with its basis. What may be listed, what is an answer slot instead, and the honest form of each kind of entry are defined once, in the prohibited-list rule of `references/question-rubric.md`. It still renders near the end of the pack; it is built second.
3. **Interviewer read** — only when real interviewer information exists. Career pattern, self-described style, what will land with them and why.
4. **Persona weights** — relationship priors adjusted by interviewer signals and by the loop, as `references/personas.md` weights them (its `(cite C…)` sources in `references/citations.md`), with the reasoning shown.
5. **Question banks** — per persona, under the coverage rules in the rubric; what a question may presuppose is defined once there too. The single most likely objection to this candidate gets the deepest rehearsal; name it as the highest-ROI prep in the pack. When a dossier named that objection, use theirs rather than inferring one, worded as the rubric's premise rule allows, and hold every guidance cell against its `prohibited_claims` and `allowed_interview_strategy` constraints.
6. **Values / principles cheat sheet** — only when section 10's condition in `references/output-template.md` holds ("detected" is defined in `references/research-checklist.md`); map each published value to a story one of the candidate's quoted sentences carries, or give a selection scaffold, with the honest branch the rubric requires, where none does.
7. **Reverse questions** — with a "why it lands" for each; at least one tied to the interviewer's own path when a profile exists. A dossier's unresolved risks and employer questions arrive interview-ready — carry them in.
8. **Delivery coaching** — only when an assessment was provided; see guardrails.

### Step 4 — Deliver

Read `references/output-template.md` and follow its skeleton and conditionality table; it applies `references/question-rubric.md`, `references/research-checklist.md` and `references/evidence-conventions.md` §2, §3 and §5 throughout. Save the pack as a markdown file and present it; offer a Word version rather than defaulting to one. End every pack with the **upgrade menu** — each missing input and what adding it would unlock. The message that presents the pack is worked, last line included, under "The message that presents the pack" in `references/output-template.md`.

Two one-line offers ride the delivery, neither of them pushed: the drill (below), and the dossier — emitting or updating `tuesday-dossier.md` with this pack's `pack_feedback`. Spec in `references/dossier-handoff.md`.

### Step 5 — Iterate

When new inputs arrive, regenerate only the affected sections and say what changed and why. A fact the candidate states outside a drill — an answer to an answer slot included — is new material: quote it into the fit snapshot and regenerate the rows that draw on it. Late structural facts (relationship, round type) justify restructuring — reweight personas, add or replace banks. Enhancers add sections. Recompute, don't patch inconsistently: no section may contradict another.

## Output discipline

Bound by `references/output-discipline.md`: its invariants are absolute, and the
parameters it names are declared here.

```text
question_budget: 3
enum_fields: confidence, gap_type, question_type
enum_columns: confidence=output-template.md#The fit snapshot/Confidence, gap_type=output-template.md#The fit snapshot/Gap type, question_type=output-template.md#Question banks/Type
closing_order: upgrade menu, drill and dossier offers, questions, watch-out
qualifier_fields: gap-and-bridge language
provenance_sections: The fit snapshot, Question banks
sibling_mentions: 1
watch_out: **Watch-out:** Suggested answers can make your experience sound bigger than what you told me — rehearse only what you actually did, in your own words.
```

`provenance` is not an enum: a Provenance cell leads with exactly one label, and in the question banks the candidate's own quoted sentences follow it —
every one the guidance's claims about their experience rest on. In the fit
snapshot the quotes sit in the evidence column and the label stands alone.

The drill and dossier offers are one line each, neither pushed.
`closing_order` governs the delivery as a whole: the pack, whose last section is
the upgrade menu, then the offers, then any questions, then the watch-out line.
When the pack is saved as a file, the offers, the questions and the watch-out line
close the message that presents it, and nothing follows the watch-out line; where
it never goes — the pack file, a drill's in-character turns — is
`references/output-discipline.md` rule 7.

## The n + x rule

`references/interaction-grammar.md` §8 binds: *n*, this spec's sections, whole; *x*, anything beyond spec, only as a one-line labeled offer of what it adds and why this engagement earns it, built on approval and never woven in silently. The offer may ride an already-needed Step 1 message; otherwise it lands with the delivered pack, like the drill offer. Flag x that keeps earning approval for codification.

## Modes

- **Session** (default): one pack for one upcoming conversation.
- **Loop**: multiple scheduled rounds → shared fit snapshot plus per-round mini-packs with per-round persona weights. Spec in `references/output-template.md`.
- **Drill**: after any pack, offer one live rehearsal — Claude adopts a persona and runs the question with reactive follow-ups, then gives feedback against **that question's own guidance cell**: the beats it named, the weakest-assumption move, the hold-then-concede structure — and an answer slot, met by either honest branch, never by the practice it names. That cell is the rubric. Spec in `references/output-template.md`.

## Input contract and degradation ladder

| Input | Tier | If missing | When to obtain |
|---|---|---|---|
| Company + role title | Gate | Can't run — the only hard requirement | At invocation |
| Full JD text | Core | Research a representative JD for the title; label JD-derived questions `[inferred]` | Ask once in Step 1; proceed if not supplied |
| Candidate CV / background | Core | Fit snapshot becomes a self-assessment worksheet; guidance becomes story-*selection* scaffolds ("pick a time you held a position under pressure…") instead of story-mapped answers — as it does, CV or not, for any question none of the candidate's sentences carries | Ask once in Step 1; proceed if declined |
| Round type + relationship to interviewer | Structural | Full-loop pack with flat persona weights — noticeably weaker; say so | Always worth the Step 1 question: cheap, un-researchable, shapes the skeleton |
| Interviewer identity / profile | Enhancer | Drop the interviewer read; personas fall back to round-type priors; reverse questions go role-generic | Never demand; research public footprint if a name is given; list in upgrade menu |
| Company research / strategy brief | Enhancer | Generated by the research module at the consented tier | Never ask — make |
| Working-style assessment | Enhancer | Drop the delivery-coaching section | Never solicit; accept if offered |
| Recruiter / HR guidance — focus areas, pre-declared deliverables, process details | Enhancer, high-leverage | Coverage assumed from round-type priors; no graded-deliverable sections | Fold into the round-and-relationship question when a Step 1 message is being sent anyway; otherwise upgrade menu — usually one email to the recruiter |
| Prep time available | Structural-lite | Default to the full pack | Fold into the Step 1 message if natural |
| `tuesday-dossier.md` from job-underwriter | Enhancer, high-leverage | Build from raw inputs as always — the standalone invariant holds. Without it, the highest-ROI objection is inferred rather than evidence-derived, weak areas carry no strategy constraint, and no `prohibited_claims` guardrail exists | Read if present; never request it as a precondition. One upgrade-menu line on what it would add |

Degrade by dropping or genericizing sections and labeling provenance — never by inventing specifics.

## Guardrails

- **Truthful attribution.** The pack coaches candidates to defend real claims precisely and shrink inflated ones gracefully — "how much of that was actually you" questions exist to rehearse honesty under pressure. Never draft answers that overstate the candidate's role or invent accomplishments. The suite's full never-do list is the truthfulness core in `references/evidence-conventions.md` §6 — it binds every cell of this pack.
- **`prohibited_claims` are absolute.** When a dossier lists a claim as prohibited, no guidance, story mapping, reverse question, answer slot, or drill feedback may assert it, soften it, or imply it — that override beats every provenance label and every persona's counter-strategy. A list built locally binds the same surfaces.
- **Interviewer research** is public professional footprint only: roles, career pattern, published talks and writing, self-descriptions. No contact-detail hunting, nothing about personal life, no personality inference beyond what they've published about themselves. When a fact about the interviewer is uncertain, drop it rather than hedge it.
- **Assessments** are delivery tuning, not content: reflect only what the document itself says, in its own framing; never extend it into diagnosis or personality typing; never suggest the candidate mention it in the interview; the answers stay the same, the packaging adapts.
- **Candidate-side only.** If an employer wants to use this to screen candidates, decline the skill and help them design a structured interview directly instead.
- **Inappropriate or illegal questions.** On request, include the protective mini-bank from `references/personas.md` — redirect techniques for age, family-status, visa-fishing and similar probes. Coach redirection and boundary-holding, never deception.

## Reference files

Each is named at the step that needs it. Mirrors copy the suite's canonical files verbatim; canonical wins on conflict.

- `references/personas.md` — read before weighting personas or writing any bank
- `references/question-rubric.md` — read before writing any question
- `references/research-checklist.md` — read before any research
- `references/output-template.md` — read before delivering
- `references/dossier-handoff.md` — read when a dossier is present, and before offering to emit one
- `references/evidence-conventions.md` (mirror)
- `references/reframing-audit.md` (mirror)
- `references/output-discipline.md` (mirror)
- `references/interaction-grammar.md` (mirror)
- `references/dossier-schema.md` (mirror)
- `references/citations.md` (mirror) — sources behind outside claims; quote nothing a `(cite C1)` entry does not hold
- `references/rationale.md` — why the rules are shaped this way; not needed to follow them
