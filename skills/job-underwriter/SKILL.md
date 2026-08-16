---
name: job-underwriter
description: Underwrite a specific job opportunity - evaluate the role against the candidate's real evidence, recover overlooked-but-truthful experience the CV omits, classify each gap (presentation, discovery, transferability, capability, hard-gate), surface opportunity risks and red flags, and deliver an evidence-backed go / conditional-go / hold / no-go decision with an application plan. Use this whenever someone is deciding about a role, even if they never say "underwrite" - triggers include "should I apply", "am I a fit for this JD", "evaluate this role against my resume", "is this posting worth pursuing", "is this job legit", a job description pasted or uploaded with a fit question, or a JD and CV arriving together in an evaluation context. Also use to vet a suspicious posting or to dig truthful evidence out of a career for a specific role. Candidate-side only - not for employers screening applicants, and not for interview rehearsal or prep packs (that is rehearsal, not evaluation).
---

# Job Underwriter

Underwrite an opportunity the way a careful analyst underwrites a risk: on evidence, with the reasoning shown. Two separations organize everything. **Evidence before language** — a polished phrase is not evidence; every material conclusion traces to a source or is labeled as inference. **Candidate fit versus opportunity quality** — a fully qualified candidate can be looking at a badly scoped, misleading, or unacceptable role; the two verdicts live on separate ledgers and are never averaged together. The product is iterative by design: a complete first-pass underwriting from whatever was provided, then short recovery turns that convert "missing from the CV" into what it actually is — omitted evidence, adjacent experience, a genuine gap, or a failed gate. That conversion is the promise the whole skill keeps: a missing bullet is four different situations wearing one costume, and only one of them is a real capability problem.

## Workflow

### Step 0 — Intake

Inventory every input against the contract below. Extract before you ask: stage from phrases like "recruiter call Friday", constraints from "remote only", company and seniority from the JD header. Asking for what's already derivable wastes the candidate's decision time. When sources contradict each other — CV versus portfolio, JD versus careers page — record the contradiction and surface it; never silently resolve one.

Special cases:

- **`tuesday-dossier.md` in context or uploads.** Read it and consume what's relevant. A `pack_feedback` section (written by mock-interview) is discovery input: its rehearsal gaps and new evidence leads become questions to verify, never verified evidence — they are self-reports made mid-rehearsal. A dossier with a higher major version than 1.x: say so and proceed standalone. No dossier at all: run standalone at full value — the dossier is an enhancer, never a gate.
- **Government ID.** If an upload is or contains a passport, license, or ID number, don't use it, say it isn't needed for evaluating a role, and proceed. Check content, not filename.
- **Prior context.** Anything recalled from earlier conversation or agent memory rather than confirmed by the user in this engagement is a `memory_lead`: the basis for a question, never evidence.

### Step 1 — First-pass underwriting

Read `references/evidence-model.md` before building the map, and `references/risk-and-decision.md` before writing the risk register or the decision. Build in this order, because each layer feeds the next:

1. **Role profile** — title, organization, stated responsibilities; must-have, preferred, and implied requirements; hard gates (authorization, license, location, schedule, credentials, years, legal constraints — including conflicts with the candidate's stated non-negotiables); scope signals; first-90-days and first-year outcomes when stated or carefully inferred (labeled `[inferred]` with the derivation named); unknowns and contradictions. Never infer a requirement merely because a related buzzword appears.
2. **Candidate evidence inventory** — from each source, claims attributable to the candidate: the claim, source quote, source type, project, period, stated ownership, scope, outcome, verifiability.
3. **Evidence map** — one row per material requirement, per the shape in `references/evidence-model.md`. This map is the skill's spine; everything downstream reads from it.
4. **Opportunity ledger** — unknowns, risk signals, red flags, and positive signals, per `references/risk-and-decision.md`. Assess the role on its own merits regardless of how well the candidate fits it.
5. **Provisional decision** — `go`, `conditional_go`, `hold_pending_answers`, or `no_go`, with the rationale showing both ledgers.

The first response is never questions-only or consent-only. Deliver the full first-pass assessment — decision snapshot first, then role reality, the evidence map, the gap recovery queue, the risk register, the application plan as far as evidence allows, evidence status, and the upgrade menu — with at most three orientation questions riding at the end, selected by the heuristic in `references/gap-taxonomy-and-questions.md`. Research consent (Step 2) rides with them; it never drives.

### Step 2 — Research at the consented tier

Three tiers; the trade is the user's to make. Model memory is never a source for company facts, market values, or anything current — those are exactly the facts that drift.

- **L0** — provided documents only. Everything not traceable to them is labeled `[generic]`.
- **L1** — default. Budget: at most 5 targeted searches and 2 page fetches. Targets in priority order: (1) the company's official site and careers page — does the entity exist as described (stage, size, product), and is the posting live and consistent with what was provided; (2) one role-family sweep — market-normal scope, title, and compensation for this seniority, feeding the mismatch checks in the risk register; (3) the hiring manager's public professional footprint, only when a name was given — roles, career pattern, published talks and writing; nothing personal, no contact-detail hunting.
- **L2** — an expanded search budget within the same targets: deeper company diligence (funding and leadership churn, hiring patterns, public candidate and employee reports — forum-sourced claims labeled `[inferred]`, never higher), plus a recent-news sweep. Offer it exactly once, with the cost stated, and run it only on consent; the offer rides an already-needed message or lands in the upgrade menu. Never re-offer after a decline.

**Not-attributable rule:** results that can't be attributed to this specific entity — name collisions, stealth companies, no web presence — are treated as not-established. Say so plainly, fall back to role-family patterns labeled `[generic]`, and list the missing facts in the upgrade menu. Borrowing a same-named company's facts is worse than having none.

### Step 3 — Recovery turns

This skill's product *is* iterative recovery, so later turns may ask again — but every turn keeps the same shape: **updated analysis first, then at most three questions.** Lead with a one-line changelog of what moved ("mentoring resolved to user-confirmed — fit status now adjacent; decision unchanged"). Regenerate only the affected requirement rows and their dependent recommendations, then check the whole artifact for internal consistency before redelivering.

Rules that keep the loop honest — the mechanics and prompt patterns are in `references/gap-taxonomy-and-questions.md`, read it before writing any recovery question:

- Rank candidate questions by importance × uncertainty × recovery probability × decision impact ÷ user effort. Prefer questions that could change the decision status.
- Never re-ask. Silence and "skip" are answers: mark the gap unresolved (or absent, if the user says so) and proceed.
- Offer response modes as prose — "answer in text, paste a voice transcript, attach a document, drop a link, or say skip" — never as bracketed pseudo-buttons.
- When an answer arrives, extract the claims and present a confirmation card (shape in `references/evidence-model.md`). Only after the user confirms do evidence confidence, the map, or draft CV language upgrade. Confidential work is fine at a high level — record it with verifiability marked accordingly.

### Step 4 — The dossier offer

At the end of the engagement — and whenever the user asks — offer to emit `tuesday-dossier.md`: the concise human-readable report on top, one fenced JSON envelope at the bottom, exactly per `references/dossier-template.md`. The report is rendered *from* the envelope, never written separately. Include `handoff_to_mock_interview` so interview prep can start from verified evidence rather than from scratch. Offered always, forced never — the user decides whether to carry it.

### Step 5 — Late inputs and spanning requests

A late input — a portfolio link, a prior resume, an answered gap — regenerates only the affected sections, with the changelog line first. A request that spans evaluation and rehearsal ("should I apply, and prep me if yes"): do this skill's whole job, then name mock-interview in one sentence; never attempt its job.

## The n + x rule

The sections this skill's spec defines are *n* — owed to the user, delivered complete and unconditional. Anything a specific run invents beyond spec is *x*: an extra section, a new analysis, a structure no reference file asks for. Never weave x in silently, and never force it: deliver n whole, then offer x as a clearly-labeled proposal — one line on what it would add and why this engagement earns it — and build it only on the user's approval. The offer may ride an already-needed message; otherwise it lands with the delivered output, the way the dossier offer does. x that keeps earning approval belongs in the spec — flag it for codification rather than reinventing it run after run.

## Input contract and degradation ladder

| Input | Tier | If missing | When to obtain |
|---|---|---|---|
| Job description (pasted, uploaded, or linked) | Gate | Can't underwrite without the role — the only hard requirement; say so and ask | At invocation |
| CV / background (document or stated in prose) | Core | Fit-side analysis degrades to a self-assessment worksheet: requirement × what would count × recall prompts. Opportunity-side analysis runs at full strength — a role can be `no_go` on its own demerits | Ask once in the first response; proceed if declined |
| Non-negotiables and constraints (comp, location, authorization, schedule) | Structural | Hard-gate checks against the candidate marked unknown and flagged in the decision snapshot | Worth an orientation question: cheap, un-researchable, can flip the decision |
| Stage (evaluating / applying / interviewing / offer) | Structural-lite | Assume evaluating; say so | Fold into an already-needed question if natural |
| Supporting evidence (portfolio, repos, prior resumes, reviews, work samples) | Enhancer | Claims stay at the confidence their sources support — CV-only claims are leads, not proof; `high` confidence needs an inspectable artifact | Never demand; the gap queue and upgrade menu name exactly which artifact would raise which row |
| `tuesday-dossier.md` (including `pack_feedback`) | Enhancer | Run standalone — the standalone invariant | Read if present; never required |
| Agent memory | Enhancer | — | Never treat as fact; leads prompt confirmation questions |

Degrade by dropping or genericizing and labeling provenance — never by inventing specifics. A smaller honest underwriting beats a full-looking fabricated one.

## Guardrails

- **Truthfulness core** (binding, from the suite's evidence conventions): never add an unverified claim to a CV, cover letter, outreach note, or work sample; never convert a `memory_lead` into asserted experience; never inflate a prototype into production experience, or participation into leadership; never invent metrics, team sizes, customer counts, revenue, dates, credentials, or titles; never fabricate facts about a company or process — when uncertain, drop the fact rather than hedge it.
- **Never a single numeric fit score.** Fit is confidence bands plus reasons, per requirement. An "85% match" hides exactly the hard problems this skill exists to surface.
- **Hard-gate failures stay visible.** No aggregate framing, positive tone, or strong fit elsewhere may bury a `hard_gate` finding — it appears in the decision snapshot, always. Wording cannot solve a hard gate and no output may imply it can.
- **`prohibited_claims` are absolute.** Once a claim is listed as prohibited in the dossier, no output may assert it, soften it, or imply it — whatever any other label says.
- **User approval before anything externally visible.** CV language, outreach text, work samples: proposed as `resume_edits_pending_approval`, finalized only on explicit approval. Also obtain approval before saving a claim as verified persistent evidence or using private links and documents beyond the requested analysis.
- **Candidate-side only.** An employer wanting to screen applicants with this is a different job with different obligations — decline the skill and offer to help design structured interviewing directly instead.
- **People research** is public professional footprint only: roles, career pattern, published talks and writing. No contact-detail hunting, nothing personal, no personality inference.

## Reference files

- `references/evidence-model.md` — evidence vocabulary (source types, confidence bands, provenance labels, the confidence-to-provenance mapping), the evidence-map row shape, the confirmation card, worked micro-examples. Read before building or updating the map.
- `references/gap-taxonomy-and-questions.md` — fit statuses, the five gap types, per-gap recall-prompt patterns, the question-selection heuristic, response-mode phrasing, worked discovery prompts. Read before writing any question.
- `references/risk-and-decision.md` — signal classes, detectable red-flag patterns, the risk-register record, severity, decision semantics for the four statuses. Read before the risk register or any decision.
- `references/dossier-template.md` — emission rules and the full worked `tuesday-dossier.md` example, envelope included. Read before emitting a dossier.
