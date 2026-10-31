---
name: job-underwriter
description: Decides whether a specific job is worth applying to, and what the real gaps are. Use this whenever someone is weighing an actual role — "should I apply", "am I a fit for this JD", "is this posting worth pursuing", "is this job legit", "am I reaching", "is it worth my time" — or pastes, uploads, or links a job description with any question about fit, gaps, or whether to bother. It maps the candidate's evidence requirement by requirement, recovers truthful experience the CV left out, classifies each gap (presentation, discovery, transferability, capability, hard-gate), flags risks and red flags in the posting itself, and returns a go / conditional-go / hold / no-go decision with an application plan. Also use to vet a suspicious or vague posting. Candidate-side only — not for employers screening applicants. Interview rehearsal and prep packs are mock-interview's; when a request spans both ("should I apply, and prep me if so"), still use this skill for the decision and name the sibling for the rehearsal.
---

# Job Underwriter

Underwrite an opportunity on evidence, with the reasoning shown. **Evidence before language** — a polished phrase is not evidence; every material conclusion traces to a source or is labeled as inference. **Candidate fit versus opportunity quality** — the two verdicts live on separate ledgers and are never averaged together.

## Before sending

Copy this list and check the response against it. Each item points to its rule and restates none; rules 1, 5 and 7 are in `references/output-discipline.md`.

```text
1. Snapshot first, read off the finished map; no recap anywhere (Step 1)
2. Every first-pass section, in Step 1's order; no questions in the gap queue (Step 1)
3. Provenance label on every derived statement (Step 1)
4. One Research tier line; one row per declared target (Step 2)
5. Questions within question_budget, counted across the message (rule 1)
6. The closing run in closing_order, nothing between its parts (Step 2)
7. Watch-out line last, exact, never in tuesday-dossier.md (rule 7)
8. Sibling named at most sibling_mentions times (rule 5)
```

## Guardrails

- **Truthfulness core.** The never-do list in `references/evidence-conventions.md` §6 binds every output of this skill; when uncertain, drop the fact rather than hedge it. Inflation hides in single words; run the reframing audit, `references/reframing-audit.md`, over everything proposed for the candidate to say, write, or send — resume lines, positioning advice, outreach, interview framing.
- **Never a single numeric fit score.** Fit is confidence bands plus reasons, per requirement.
- **Hard-gate failures stay visible.** No aggregate framing, positive tone, or strong fit elsewhere may bury a `hard_gate` finding — it appears in the decision snapshot's hard-gates line, always. Wording cannot solve a hard gate and no output may imply it can.
- **`prohibited_claims` are absolute.** Once a claim is listed as prohibited in the dossier, no output may assert it, soften it, or imply it — whatever any other label says.
- **User approval before anything externally visible.** CV language, positioning and outreach text, work samples: proposed as `resume_edits_pending_approval`, finalized only on explicit approval — and the approval statement sits where it visibly covers the prose advice as well as any table. Also obtain approval before saving a claim as verified persistent evidence or using private links and documents beyond the requested analysis.
- **Candidate-side only.** An employer wanting to screen applicants with this: decline the skill and offer to help design structured interviewing directly instead.
- **People research** is public professional footprint only: roles, career pattern, published talks and writing. No contact-detail hunting, nothing personal, no personality inference.

## Workflow

### Step 0 — Intake

Inventory every input against the contract below. Extract before you ask: stage from phrases like "recruiter call Friday", constraints from "remote only", company and seniority from the JD header. When sources contradict each other — CV versus portfolio, JD versus careers page — record the contradiction and surface it; never silently resolve one.

Special cases:

- **`tuesday-dossier.md` in context or uploads.** Read it with `references/dossier-schema.md` §3 and §7 (versioning, `pack_feedback`) and consume what's relevant. A `pack_feedback` section (written by mock-interview) is discovery input: its rehearsal gaps and new evidence leads become questions to verify, never verified evidence. A dossier with a higher major version than 1.x: say so and proceed standalone. No dossier at all: run standalone at full value — the dossier is an enhancer, never a gate.
- **Government ID.** If an upload is or contains a passport, license, or ID number, don't use it, say it isn't needed for evaluating a role, and proceed. Check content, not filename.
- **Prior context.** Anything recalled from earlier conversation or agent memory rather than confirmed by the user in this engagement is a `memory_lead`: the basis for a question, never evidence.

### Step 1 — First-pass underwriting

Before building the map, read `references/evidence-conventions.md` (vocabulary; its cites in `references/citations.md`), `references/evidence-model.md` (row shape) and `references/gap-taxonomy-and-questions.md` (each row's fit and gap calls); before the register or the decision, `references/risk-and-decision.md`; for where a claim about the world sits, `references/output-discipline.md` rule 6; for the worked sections, `references/dossier-worked-report.md`. Build in this order:

1. **Role profile** — title, organization, stated responsibilities; must-have, preferred, and implied requirements; hard gates (authorization, license, location, schedule, pay, travel, credentials, legal constraints — terms, never a length of experience, as `references/evidence-conventions.md` §3 defines a gate — including the candidate's stated non-negotiables, each of which the role's terms touch is carried by one `hard_gate` row in the map — the JD's own row for that term where it has one, otherwise a row of its own, per `references/evidence-model.md`); scope signals; first-90-days and first-year outcomes when stated or carefully inferred (labeled `[inferred]` with the derivation named); unknowns and contradictions. Never infer a requirement merely because a related buzzword appears.
   - Where research reached the role-family sweep, close role reality with a **market calibration** line: where this title, seniority, and scope sit against role-family norms, labeled `[generic]` — it is a pattern, not a claim about this employer.
   - Stated compensation gets calibrated against that band — the band is `[generic]`, the posting's own figure is `[grounded]` from the JD, and the comparison goes in the mismatch entry in the risk register.
   - For unstated compensation, the band against the candidate's floor, filed the way RR2 in `references/dossier-worked-report.md` files an unstated term against a hard constraint; unstated compensation gets the band plus the observation that the posting withholds it, which is itself worth a question.
2. **Candidate evidence inventory** — from each source, claims attributable to the candidate: the claim, source quote, source type, project, period, stated ownership, scope, outcome, verifiability.
3. **Evidence map** — one row per material requirement, per the shape in `references/evidence-model.md`. Everything downstream reads from it.
4. **Opportunity ledger** — unknowns, risk signals, red flags, and positive signals, per `references/risk-and-decision.md`. Assess the role on its own merits regardless of how well the candidate fits it.
5. **Provisional decision** — `go`, `conditional_go`, `hold_pending_answers`, or `no_go`, with the rationale showing both ledgers.
6. **The snapshot, read off the finished map** — its fit ledger projected from the map's #, Priority, Fit and Requirement columns into the shape of slot 2 in `references/risk-and-decision.md` (one line per Priority tier in enum order, each grouped by Fit in enum order, every row exactly once), its hard-gates line from the `hard_gate` rows — every one named with its fit, failed rows first, in the form rule 4 of `references/risk-and-decision.md` gives — and any confidence band from the Confidence column of the one row it sits beside. The snapshot is delivered first and built last.

The first response is never questions-only or consent-only. Deliver the full first-pass assessment — decision snapshot first, then role reality, the evidence map, the gap recovery queue, the risk register, the application plan as far as evidence allows, and evidence status — then the one-line dossier offer, the upgrade menu, at most three orientation questions selected by the heuristic in `references/gap-taxonomy-and-questions.md`, and the watch-out line closing the message. **The decision snapshot is the assessment's one summary, and it comes first:** nothing restates it — no "bottom line", recap or closing summary anywhere in the response, not only at its end. **The gap recovery queue holds no questions** — its rows say what each gap is and what would close it, and the question each row implies is asked in the closing block, tagged with its row id. Research consent (Step 2) rides with the questions; it never drives.

The dossier offer (Step 4) and, after it, the upgrade menu (each missing input and what it concretely unlocks) stand in every delivered assessment, first pass included. Label what you wrote: any statement derived from research or inference carries its provenance — `[grounded]`, `[inferred]`, or `[generic]` — where it appears.

### Step 2 — Research at the consented tier

Three tiers; the trade is the user's to make. Model memory is never a source for company facts, market values, or anything current.

- **L0** — provided documents only, chosen by the user or forced because the host offers no search, as `references/interaction-grammar.md` §4 defines it: no search and no fetch of the skill's choosing, and a link the user gave you to read is a provided document. Everything else labeled `[generic]`; the upgrade menu says what research would have added.
- **L1** — default. Budget: at most 5 targeted searches and 2 page fetches. Targets in priority order: (1) the company's official site and careers page — does the entity exist as described (stage, size, product), and is the posting live and consistent with what was provided — feeding role reality's organization and contradictions rows and the failed-attribution entry in the risk register; (2) one role-family sweep — market-normal scope, title, and compensation for this seniority — feeding the market calibration line and the mismatch checks in the risk register; (3) the hiring manager's public professional footprint, only when a name was given and only within the people-research guardrail — feeding role reality's scope read and the application plan's positioning — which verified story to lead with for this reader.
- **L2** — two further targets, numbered after L1's, with at most 5 further searches and 2 further fetches: (4) deeper company diligence — funding and leadership churn, hiring patterns, public candidate and employee reports, forum-sourced claims labeled `[inferred]`, never higher — feeding the risk register; (5) a recent-news sweep, feeding the risk register and the opportunity ledger. Offer it exactly once, its cost stated as its caps ("up to 5 more searches and 2 more fetches"), on an already-needed message or in the upgrade menu; run it only on consent, and never re-offer after a decline.

**Not-attributable rule** (`references/interaction-grammar.md` §4): a result that can't be attributed to this specific entity — a name collision, a stealth company, no web presence — is not-established. Say so plainly, fall back to role-family patterns labeled `[generic]`, and list the missing facts in the upgrade menu.

**Budget accounting is one line, and it stays true.** Directly above the accounting table: `Research tier: L1 — searches 3 of 5, fetches 1 of 2`, or `Research tier: L0 — no searches`, or at L2 `Research tier: L2 — searches 6 of 10, fetches 2 of 4`, the caps added together. It counts every call this skill chose to send in the engagement, refused ones included. Reading a link the user gave you to read is reading an input, not research: it is named on the same line — `; user links read 1` — and never charged to the budget; what counts as such a link, and what is a research call instead, is `references/interaction-grammar.md` §4. No other sentence restates the line: no "attempted", no second tally in the prose.

**Every declared target is accounted for, in evidence status:** one row per declared
target — L1's three, then L2's two when L2 ran, numbered in that order — holding
the target, a Status cell of exactly one of `yes`, `skipped`, `n/a` or
`unavailable`, and the reason. Each label and its ground are
`references/interaction-grammar.md` §4's; read it before writing the table.
Searches go only to declared targets. Every `yes` row names the queries and pages
it rests on, each page by its title or address. Worked table: Evidence status in
`references/dossier-worked-report.md`.

Failed attribution is also a finding about the opportunity: when L1 cannot confirm that the employer exists as described, that goes in the risk register as a standing entry (shape in `references/risk-and-decision.md`) and it constrains the decision — an unverified employer is a reason a `go` becomes `conditional_go` pending verification. Say what would resolve it: a link to the live posting, the company's own careers page, the recruiter's email domain.

**Closing order is fixed: the dossier offer, then the upgrade menu, then the questions, then the watch-out line — and nothing between them or after it.** The watch-out line is the fixed `watch_out` sentence below, placed as `references/output-discipline.md` rule 7 places it. No recap closes the message either, because the snapshot at the top is its one summary (Step 1). The response-modes line is part of the questions — after each question, or once after the last for all of them — not something after them.

### Step 3 — Recovery turns

Later turns may ask again, but every turn keeps the same shape: **updated analysis first, then at most three questions, then the watch-out line.** Lead with a one-line changelog of what moved ("panel chairing resolved to user-confirmed — fit status now adjacent; decision unchanged"). Regenerate only the affected requirement rows and their dependent recommendations, then check the whole artifact for internal consistency before redelivering.

Read `references/gap-taxonomy-and-questions.md` before writing any recovery question — its ranking, its rules (never re-ask; silence and "skip" are answers) and its response modes, offered as prose, never as bracketed pseudo-buttons — and `references/reframing-audit.md` before any repositioning proposal it calls for. When an answer arrives, extract the claims and present a confirmation card (shape in `references/evidence-model.md`); only after the user confirms do evidence confidence, the map, or draft CV language upgrade. Confidential work is fine at a high level — record it with verifiability marked accordingly.

### Step 4 — The dossier offer

The dossier offer is one sentence, no pressure, immediately before the upgrade menu; at the natural end of the engagement, or whenever the user asks, it is made directly. Offered always, forced never. Emitting it produces `tuesday-dossier.md` exactly per `references/dossier-emission.md` — report on top, rendered from the one fenced JSON envelope at the bottom as `references/dossier-schema.md` §2 defines — worked in `references/dossier-worked-report.md` and `references/dossier-worked-envelope.md`, with `handoff_to_mock_interview` keyed as `references/dossier-schema.md` §6 defines. The watch-out line closes the message that offers or presents the file, never the file (`references/output-discipline.md` rule 7).

### Step 5 — Late inputs and spanning requests

A late input — a portfolio link, a prior resume, an answered gap — regenerates only the affected sections, with the changelog line first. A request that spans evaluation and rehearsal ("should I apply, and prep me if yes"): do this skill's whole job, then name mock-interview in one sentence; never attempt its job.

## Output discipline

Bound by `references/output-discipline.md`: its invariants are absolute, and the
parameters it names are declared here.

```text
question_budget: 3
enum_fields: priority, fit_status, confidence, gap_type, class, severity
enum_columns: priority=dossier-worked-report.md#Evidence map/Priority, fit_status=dossier-worked-report.md#Evidence map/Fit, confidence=dossier-worked-report.md#Evidence map/Confidence, gap_type=dossier-worked-report.md#Evidence map/Gap, class=dossier-worked-report.md#Opportunity risk register/Class, severity=dossier-worked-report.md#Opportunity risk register/Severity
closing_order: dossier offer, upgrade menu, questions, watch-out
qualifier_fields: reasoning, hypothesis
provenance_sections: Role reality, Evidence map, Gap recovery queue, Opportunity risk register, Application plan
sibling_mentions: 1
watch_out: A summary line here can contradict the evidence table — before you act on a count, an "only" or an all-clear, check it against the table's rows.
```

## The n + x rule

`references/interaction-grammar.md` §8 binds: *n*, this spec's sections, whole; *x*, anything beyond spec, only as a one-line labeled offer of what it adds and why this engagement earns it, built on approval. The offer rides an already-needed message or lands with the delivered output, never after the questions. Label it in prose: square brackets are reserved for the provenance labels `[grounded]`, `[inferred]`, and `[generic]` (`references/output-discipline.md` rule 3).

## Input contract and degradation ladder

| Input | Tier | If missing | When to obtain |
|---|---|---|---|
| Job description (pasted, uploaded, or linked) | Gate | Can't underwrite without the role — the only hard requirement; say so and ask | At invocation |
| CV / background (document or stated in prose) | Core | Fit-side analysis degrades to a self-assessment worksheet: requirement × what would count × recall prompts. Opportunity-side analysis runs at full strength — a role can be `no_go` on its own demerits | Ask once in the first response; proceed if declined |
| Non-negotiables and constraints (comp, location, authorization, schedule) | Structural | Hard-gate checks against the candidate marked unknown and flagged in the decision snapshot | Worth an orientation question |
| Stage (evaluating / applying / interviewing / offer) | Structural-lite | Assume evaluating; say so | Fold into an already-needed question if natural |
| Supporting evidence (portfolio, repos, prior resumes, reviews, work samples) | Enhancer | Claims stay at the confidence their sources support — CV-only claims are leads, not proof; the `high` band is earned as `references/evidence-conventions.md` §2 defines it | Never demand; the gap queue and upgrade menu name exactly which artifact would raise which row |
| `tuesday-dossier.md` (including `pack_feedback`) | Enhancer | Run standalone — the standalone invariant | Read if present; never required |
| Agent memory | Enhancer | — | Never treat as fact; leads prompt confirmation questions |

Degrade by dropping or genericizing and labeling provenance — never by inventing specifics.

## Reference files

Each is named at the step that needs it. Mirrors copy the suite's canonical files verbatim; canonical wins on conflict.

- `references/evidence-conventions.md` (mirror)
- `references/evidence-model.md`
- `references/gap-taxonomy-and-questions.md`
- `references/risk-and-decision.md`
- `references/reframing-audit.md` (mirror)
- `references/output-discipline.md` (mirror)
- `references/interaction-grammar.md` (mirror)
- `references/dossier-worked-report.md`, `references/dossier-emission.md`, `references/dossier-worked-envelope.md`
- `references/dossier-schema.md` (mirror) — read when a dossier is present
- `references/citations.md` (mirror) — sources behind outside claims; quote nothing a `(cite C1)` entry does not hold
- `references/rationale.md` — why the rules are shaped this way; not needed to follow them
