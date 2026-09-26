---
name: mock-interview
description: Generate a personalized mock-interview prep pack — persona-categorized question banks with grounded answer guidance and rationale, a fit-gap map, company-values alignment, reverse questions, and optional live drill sessions where Claude plays the interviewer. Use this whenever someone is preparing for a job interview, even if they don't say "mock interview" — triggers include "prep me for my interview", "interview questions for this role", "help me practice for my interview at X", "how should I answer questions about my background", an uploaded job description and/or CV in an interview context, or any mention of an upcoming recruiter screen, hiring-manager round, panel, or final round. Also use when tailoring prep to a specific interviewer or company. Candidate-side preparation only — not for employers screening candidates, and not for deciding whether to apply or whether a role is worth pursuing (that is evaluation, not rehearsal).
---

# Mock Interview

Build a prep pack a candidate can actually rehearse from. Two axes organize everything: **personas** describe how the interview will feel (who is asking, in what style), and **question types** describe what is being scored. Every question in the pack carries answer guidance grounded in the candidate's real material plus a rationale explaining why it's included and why it's categorized that way — because a candidate who understands *why* a question exists answers the follow-up, not just the question.

The pack's credibility rests on a grounding discipline: everything is either traceable to a provided document, traceable to research, or explicitly labeled as generic. A fabricated specific — an invented interviewer fact, a made-up company round — can burn the candidate in the live interview, which is worse than no pack at all.

## Workflow

### Step 0 — Intake and classification

Inventory every provided input against the contract below. Extract before you ask: seniority and team from an interviewer profile, company and level from a JD, round type from phrases like "final round" or "chat with the hiring manager". Asking for something already derivable wastes the candidate's prep time.

Three special cases:

- **`tuesday-dossier.md` in context or uploads.** Read `references/dossier-handoff.md` and consume it: `handoff_to_mock_interview` carries verified evidence, allowed strategies per weak area, the objection worth the deepest rehearsal, risks and employer questions for the reverse bank, and absolute `prohibited_claims`; `role_profile` satisfies the JD tier. A dossier sharpens the pack — it never gates it, and a pack built without one is still a complete pack.
- **Government ID.** If an upload is or contains a passport, license, or ID number, don't use it, tell the user it isn't needed for interview prep, and proceed without it. (Files named "passport" are sometimes benign profile summaries — check content, not filename.)
- **Personality / working-style assessments.** Accept if offered; never solicit one. They feed only the delivery-coaching section (Step 3) under the guardrails below.

### Step 1 — Elicit only what shapes the skeleton, and never before delivering

**A clarifying message never travels alone.** Whatever is missing, build a complete pack from what is available and deliver it in the same message as the questions: state in one line the assumption it was built on, and frame each question as what would restructure it. A turn that asks and delivers nothing leaves a candidate with an interview on Thursday holding three questions and no preparation, and it breaks the suite's one rule — every skill runs to a complete, useful output from raw inputs. The degradation ladder below exists precisely so that a pack can be built without the answers; use it rather than waiting. Delivering does not retire the questions either — whatever is missing from (a) to (c) is still asked, in that same message. A pack shipped with no questions attached has quietly decided the assumptions are good enough, which is the user's call and not this skill's.

Ask at most three questions, covering only what's missing from: (a) **round type and relationship to the interviewer(s)** — manager, peer, skip-level, cross-functional, recruiter — folding in any recruiter/HR guidance in the same breath: stated focus areas, pre-declared deliverables (a POV, a presentation, a take-home), process details; (b) **JD and/or CV** if absent, with an explicit offer to proceed without — a dossier's `role_profile` and `verified_candidate_evidence` satisfy these tiers, so with one in hand neither is asked for and both drop to upgrade-menu lines; (c) **research depth consent** (Step 2).

The consent item rides along; it never drives. If (a) and (b) are already satisfied, ask nothing — generate at the default research tier and place the deep-research offer in the upgrade menu instead. A message whose only content is an optional offer costs the user a round-trip for nothing.

Why so strict: everything else is either researchable — never ask the user what the web knows — or an enhancer that must not gate generation. Round-and-relationship earns its slot because it's cheap to answer, impossible to research, and reshapes the whole pack; a late-arriving "actually he'll be my peer" forces structural rework rather than an added section. That is the reason to ask it in the first message — not a reason to withhold the pack until it is answered.

If the user declines or doesn't answer, proceed down the degradation ladder. Never re-ask.

### Step 2 — Research at the consented tier

Read `references/research-checklist.md`. Three tiers: **L0** (provided docs only), **L1** (default: at most 6 searches and 2 page fetches, spent only where a result could change the pack — official values, documented loop structure, one recent-strategy sweep, interviewer public footprint if named), **L2** (deep research: strategy brief, interviewer talks and writing, role-family loop reports — offered once, with the time cost stated, and run only on consent).

Company values, loop structure, and current strategy must come from research or provided docs, not from model memory — these are exactly the facts that drift.

### Step 3 — Synthesize

Read `references/personas.md` and `references/question-rubric.md` before writing any question, and `references/reframing-audit.md` before writing any guidance cell — every one of them is a sentence the candidate will speak aloud. Build in this order, because each layer feeds the next:

1. **Fit snapshot** — JD requirement × candidate evidence × gap-and-bridge language. The gaps found here become the Skeptic and Pressure banks' best material. With a dossier in hand, the underwriter's `evidence_map` supplies these rows already graded — its confidence bands and gap types are the vocabulary this skill uses too, per the mirror in `references/evidence-conventions.md`.
2. **Interviewer read** — only when real interviewer information exists. Career pattern, self-described style, what will land with them and why.
3. **Persona weights** — relationship priors adjusted by interviewer signals and company archetype, with the reasoning shown.
4. **Question banks** — per persona, under the coverage rules in the rubric. The single most likely objection to this candidate gets the deepest rehearsal; name it as the highest-ROI prep in the pack. When a dossier named that objection, use theirs rather than inferring one, and hold every guidance cell against its `prohibited_claims` and `allowed_interview_strategy` constraints.
5. **Values / principles cheat sheet** — only when a values-style round is detected; map each published value to a specific candidate story.
6. **Reverse questions** — with a "why it lands" for each; at least one tied to the interviewer's own path when a profile exists. A dossier's unresolved risks and employer questions arrive interview-ready — carry them in.
7. **Prohibited claims** — the claims this pack will not coach, and why. With a dossier, `prohibited_claims` arrives from the underwriter and binds every guidance cell. **Without one, build it locally** from the fit snapshot's gaps: the claims a candidate might reach for under pressure that their material does not support. The temptations are identical either way, and both sibling skills maintain such a list — a pack that carries one only when a dossier happens to be present is protected by luck.
8. **Delivery coaching** — only when an assessment was provided; see guardrails.

### Step 4 — Deliver

Read `references/output-template.md` and follow its skeleton and conditionality table. Save the pack as a markdown file and present it; offer a Word version rather than defaulting to one. End every pack with the **upgrade menu** — each missing input and what adding it would unlock. The menu is how enhancers arrive without ever gating on them: make the value of more input visible and let the user pull.

Two one-line offers ride the delivery, neither of them pushed: the drill (below), and the dossier — emitting or updating `tuesday-dossier.md` with this pack's `pack_feedback`, so the objections and gaps rehearsal exposed travel back to the underwriter as leads. Spec in `references/dossier-handoff.md`.

### Step 5 — Iterate

When new inputs arrive, regenerate only the affected sections and say what changed and why. Late structural facts (relationship, round type) justify restructuring — reweight personas, add or replace banks. Enhancers add sections. Recompute, don't patch inconsistently: a pack that says "hiring manager" in one section and "peer" in another is worse than either.

## Output discipline

Bound by `references/output-discipline.md`, the suite's canonical rules on the
shape of a delivered response, mirrored verbatim into this skill. Its invariants
are absolute; the parameters it names are declared here.

```text
question_budget: 3
enum_fields: confidence, gap_type, question_type
closing_order: upgrade menu, drill and dossier offers, questions
qualifier_fields: gap-and-bridge language
provenance_sections: The fit snapshot
sibling_mentions: 1
```

`provenance` is not declared an enum: a Provenance cell leads with exactly one
label, and in the question banks the candidate's own quoted sentence follows it
wherever guidance coaches a claim about their experience. In the fit snapshot the
label stands alone.

The drill and dossier offers sit inside the closing run because they are things
the candidate acts on, not commentary on the pack — one line each, neither pushed.
`closing_order` governs the delivery as a whole: the pack, whose last section is
the upgrade menu, then the offers, then any questions. When the pack is saved as a
file, the offers and questions close the message that presents it, and nothing
follows the questions.

## The n + x rule

The sections this skill's spec defines are *n* — owed to the user, delivered complete and unconditional. Anything a specific run invents beyond spec is *x*: an extra section, a new analysis, a structure no reference file asks for. Never weave x in silently, and never force it: deliver n whole, then offer x as a clearly-labeled proposal — one line on what it would add and why this engagement earns it — and build it only on the user's approval. The offer may ride an already-needed Step 1 message; otherwise it lands with the delivered pack, like the drill offer. x that keeps earning approval belongs in the spec — flag it for codification rather than reinventing it run after run.

## Modes

- **Session** (default): one pack for one upcoming conversation.
- **Loop**: multiple scheduled rounds → shared fit snapshot plus per-round mini-packs with per-round persona weights. Spec in `references/output-template.md`.
- **Drill**: after any pack, offer one live rehearsal — Claude adopts a persona and runs the question with reactive follow-ups, then gives feedback against **that question's own guidance cell**: the beats it named, the weakest-assumption move, the hold-then-concede structure. That cell is the rubric, which is why the pack is written before the drill and why a drill on a question whose guidance was generic can only give generic feedback. Spec in `references/output-template.md`. The pack is preparation; the drill is transfer.

## Input contract and degradation ladder

| Input | Tier | If missing | When to obtain |
|---|---|---|---|
| Company + role title | Gate | Can't run — the only hard requirement | At invocation |
| Full JD text | Core | Research a representative JD for the title; label JD-derived questions `[inferred]` | Ask once in Step 1; proceed if not supplied |
| Candidate CV / background | Core | Fit snapshot becomes a self-assessment worksheet; guidance becomes story-*selection* scaffolds ("pick a time you held a position under pressure…") instead of story-mapped answers | Ask once in Step 1; proceed if declined |
| Round type + relationship to interviewer | Structural | Full-loop pack with flat persona weights — noticeably weaker; say so | Always worth the Step 1 question: cheap, un-researchable, shapes the skeleton |
| Interviewer identity / profile | Enhancer | Drop the interviewer read; personas fall back to round-type priors; reverse questions go role-generic | Never demand; research public footprint if a name is given; list in upgrade menu |
| Company research / strategy brief | Enhancer | Generated by the research module at the consented tier | Never ask — make |
| Working-style assessment | Enhancer | Drop the delivery-coaching section | Never solicit; accept if offered |
| Recruiter / HR guidance — focus areas, pre-declared deliverables, process details | Enhancer, high-leverage | Coverage assumed from round-type priors; no graded-deliverable sections | Fold into the round-and-relationship question when a Step 1 message is being sent anyway; otherwise upgrade menu — usually one email to the recruiter |
| Prep time available | Structural-lite | Default to the full pack | Fold into the Step 1 message if natural |
| `tuesday-dossier.md` from job-underwriter | Enhancer, high-leverage | Build from raw inputs as always — the standalone invariant holds. Without it, the highest-ROI objection is inferred rather than evidence-derived, weak areas carry no strategy constraint, and no `prohibited_claims` guardrail exists | Read if present; never request it as a precondition. One upgrade-menu line on what it would add |

Degrade by dropping or genericizing sections and labeling provenance — never by inventing specifics. A smaller honest pack beats a full-looking fabricated one.

## Guardrails

- **Truthful attribution.** The pack coaches candidates to defend real claims precisely and shrink inflated ones gracefully — "how much of that was actually you" questions exist to rehearse honesty under pressure, because interviewers ask them and candor is scored. Never draft answers that overstate the candidate's role or invent accomplishments. The suite's full never-do list is the truthfulness core in `references/evidence-conventions.md` §6 — it binds every cell of this pack.
- **`prohibited_claims` are absolute.** When a dossier lists a claim as prohibited, no guidance, story mapping, reverse question, or drill feedback may assert it, soften it, or imply it — that override beats every provenance label and every persona's counter-strategy.
- **Interviewer research** is public professional footprint only: roles, career pattern, published talks and writing, self-descriptions. No contact-detail hunting, nothing about personal life, no personality inference beyond what they've published about themselves. When a fact about the interviewer is uncertain, drop it rather than hedge it — the candidate may repeat it live.
- **Assessments** are delivery tuning, not content: reflect only what the document itself says, in its own framing; never extend it into diagnosis or personality typing; never suggest the candidate mention it in the interview; the answers stay the same, the packaging adapts.
- **Candidate-side only.** If an employer wants to use this to screen candidates, that's a different job with different obligations — decline the skill and help them design a structured interview directly instead. This skill's guidance is deliberately asymmetric coaching.
- **Inappropriate or illegal questions.** On request, include the protective mini-bank from `references/personas.md` — redirect techniques for age, family-status, visa-fishing and similar probes. Coach redirection and boundary-holding, never deception.

## Reference files

- `references/personas.md` — the persona taxonomy, relationship priors, interviewer-signal adjustments, protective mini-bank. Read before weighting personas or writing any bank.
- `references/question-rubric.md` — the five question types, coverage rules, guidance-writing rules. Read before writing any question.
- `references/research-checklist.md` — tier definitions, search targets, budgets, freshness rules, company-archetype fallbacks. Read before any research.
- `references/output-template.md` — pack skeleton, conditionality table, loop-mode and drill-mode specs, file conventions. Read before delivering.
- `references/interaction-grammar.md` — the suite's canonical interaction rules, mirrored verbatim: the standalone invariant, the elicitation policy, the research tiers and the depth rule that bounds them, privacy scope, and the n + x rule. Canonical wins on conflict.
- `references/dossier-schema.md` — the canonical dossier contract, mirrored verbatim: envelope, versioning, and which sections this skill reads versus owns.
- `references/citations.md` — the suite's recorded sources, mirrored verbatim: every figure, research finding, survey result and statement of law the conventions and references make, quoted exactly beside its source, with what weakens it. A `(cite C1)` elsewhere points here; quote nothing from a source that its entry does not hold.
- `references/dossier-handoff.md` — reading `handoff_to_mock_interview` (the five consumption rules) and writing `pack_feedback`. Read when a dossier is present, and before offering to emit one.
- `references/evidence-conventions.md` — the suite's canonical vocabulary, mirrored: source types, confidence bands, the gap taxonomy, provenance labels, and the truthfulness core. This is where the labels used throughout the pack are defined; the mirror is a verbatim copy and canonical wins on conflict.
