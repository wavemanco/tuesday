---
name: job-underwriter
description: Decide whether a specific job is worth applying to, and what the real gaps are. Use this whenever someone is weighing an actual role — "should I apply", "am I a fit for this JD", "is this posting worth pursuing", "is this job legit", "am I reaching", "is it worth my time" — or pastes, uploads, or links a job description with any question about fit, gaps, or whether to bother. It maps the candidate's evidence requirement by requirement, recovers truthful experience the CV left out, classifies each gap (presentation, discovery, transferability, capability, hard-gate), flags risks and red flags in the posting itself, and returns a go / conditional-go / hold / no-go decision with an application plan. Also use to vet a suspicious or vague posting. Candidate-side only — not for employers screening applicants. Interview rehearsal and prep packs are mock-interview's; when a request spans both ("should I apply, and prep me if so"), still use this skill for the decision and name the sibling for the rehearsal.
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

Read `references/evidence-conventions.md` for the vocabulary and `references/evidence-model.md` for the row shape before building the map, and `references/risk-and-decision.md` before writing the risk register or the decision. Build in this order, because each layer feeds the next:

1. **Role profile** — title, organization, stated responsibilities; must-have, preferred, and implied requirements; hard gates (authorization, license, location, schedule, credentials, years, legal constraints — including the candidate's stated non-negotiables, each of which the role's terms touch is carried by one `hard_gate` row in the map — the JD's own row for that term where it has one, otherwise a row of its own, per `references/evidence-model.md`); scope signals; first-90-days and first-year outcomes when stated or carefully inferred (labeled `[inferred]` with the derivation named); unknowns and contradictions. Never infer a requirement merely because a related buzzword appears. Where research reached the role-family sweep, close role reality with a **market calibration** line: where this title, seniority, and scope sit against role-family norms, labeled `[generic]` — it is a pattern, not a claim about this employer. Stated compensation gets calibrated against that band — the band is `[generic]`, the posting's own figure is `[grounded]` from the JD, and the comparison goes in the mismatch entry in the risk register — for unstated compensation, the band against the candidate's floor, as RR2 in `references/dossier-template.md` shows; unstated compensation gets the band plus the observation that the posting withholds it, which is itself worth a question.
2. **Candidate evidence inventory** — from each source, claims attributable to the candidate: the claim, source quote, source type, project, period, stated ownership, scope, outcome, verifiability.
3. **Evidence map** — one row per material requirement, per the shape in `references/evidence-model.md`. This map is the skill's spine; everything downstream reads from it.
4. **Opportunity ledger** — unknowns, risk signals, red flags, and positive signals, per `references/risk-and-decision.md`. Assess the role on its own merits regardless of how well the candidate fits it.
5. **Provisional decision** — `go`, `conditional_go`, `hold_pending_answers`, or `no_go`, with the rationale showing both ledgers.
6. **The snapshot, read off the finished map** — its fit ledger projected from the map's #, Priority, Fit and Requirement columns into the shape of slot 2 in `references/risk-and-decision.md` (one line per Priority tier in enum order, each grouped by Fit in enum order, every row exactly once), its hard-gates line from the `hard_gate` rows — every one named with its fit, failed rows first, in the form rule 4 of `references/risk-and-decision.md` gives — and any confidence band from the Confidence column of the one row it sits beside. The snapshot is delivered first and built last: written from memory of the map rather than from the map, it is where a row added late goes missing and a band goes stale.

The first response is never questions-only or consent-only. Deliver the full first-pass assessment — decision snapshot first, then role reality, the evidence map, the gap recovery queue, the risk register, the application plan as far as evidence allows, and evidence status — then the one-line dossier offer, the upgrade menu, and at most three orientation questions closing the message, selected by the heuristic in `references/gap-taxonomy-and-questions.md`. **The gap recovery queue holds no questions** — its rows say what each gap is and what would close it, and the question each row implies is asked in the closing block, tagged with its row id. A `Question:` line inside the queue puts questions fourth of nine sections and gives the message two question sites, and both of those are rules this skill already carries. Research consent (Step 2) rides with the questions; it never drives.

Two lines are standing parts of every delivered assessment, first pass included: the one-line dossier offer (Step 4) and, after it, the upgrade menu (each missing input and what it concretely unlocks). And label what you wrote: any statement derived from research or inference carries its provenance — `[grounded]`, `[inferred]`, or `[generic]` — where it appears, so the reader can always see how far the evidence goes.

### Step 2 — Research at the consented tier

Three tiers; the trade is the user's to make. Model memory is never a source for company facts, market values, or anything current — those are exactly the facts that drift.

- **L0** — provided documents only: chosen by the user, or forced because the host offers no search. L0 sends no search and no fetch of the skill's choosing. A link the user gave you to read is a provided document, read when the host can fetch it and named on the tally line; a host that cannot fetch says so and uses only what was pasted. Everything else labeled `[generic]`. The upgrade menu says what research would have added.
- **L1** — default. Budget: at most 5 targeted searches and 2 page fetches. Targets in priority order: (1) the company's official site and careers page — does the entity exist as described (stage, size, product), and is the posting live and consistent with what was provided — feeding role reality's organization and contradictions rows and the failed-attribution entry in the risk register; (2) one role-family sweep — market-normal scope, title, and compensation for this seniority — feeding the market calibration line and the mismatch checks in the risk register; (3) the hiring manager's public professional footprint, only when a name was given — roles, career pattern, published talks and writing; nothing personal, no contact-detail hunting — feeding role reality's scope read and the application plan's positioning — which verified story to lead with for this reader.
- **L2** — two further targets, numbered after L1's, with at most 5 further searches and 2 further fetches: (4) deeper company diligence — funding and leadership churn, hiring patterns, public candidate and employee reports, forum-sourced claims labeled `[inferred]`, never higher — feeding the risk register; (5) a recent-news sweep, feeding the risk register and the opportunity ledger. Offer it exactly once, with the cost stated as its caps ("up to 5 more searches and 2 more fetches"), and run it only on consent; the offer rides an already-needed message or lands in the upgrade menu. Never re-offer after a decline.

**Not-attributable rule:** results that can't be attributed to this specific entity — name collisions, stealth companies, no web presence — are treated as not-established. Say so plainly, fall back to role-family patterns labeled `[generic]`, and list the missing facts in the upgrade menu. Borrowing a same-named company's facts is worse than having none.

**Budget accounting is one line, and it stays true.** Directly above the accounting table: `Research tier: L1 — searches 3 of 5, fetches 1 of 2`, or `Research tier: L0 — no searches`, or at L2 `Research tier: L2 — searches 6 of 10, fetches 2 of 4`, the caps added together. It counts every call this skill chose to send in the engagement, refused ones included. Reading a link the user gave you to read — a JD or a portfolio they linked rather than pasted — is reading an input, not research: it is named on the same line — `; user links read 1` — and never charged to the budget. A URL the user names as the source of text they pasted ("copied from …") is not a link to read: that content is already in hand, and fetching it, or any other page on that site, is a research call, charged and attributed to the target the page serves like any other. No other sentence restates the line: no "attempted", no second tally in the prose. A count stated twice can disagree with itself, and then the reader cannot tell which of the two is the mistake.

**Every declared target is accounted for, in evidence status.** One row per
declared target — L1's three, then L2's two when L2 ran, numbered in that order —
three columns: the target, a Status cell holding exactly one of `yes`, `skipped`,
`n/a` or `unavailable`, and the reason. Searches go only to declared targets; a
question none of them covers is an upgrade-menu line. The label follows what
happened, facts first. A target a search was sent for is `yes` if any call
returned a result — an empty or unattributable one included, which the row says
as "not established" — and `unavailable` only if every call was refused or
errored. A target no search was sent for is `n/a` if the inputs cannot form its
query (no hiring manager was named); `skipped` if the inputs already fix every
output it feeds, named in the row — the only ground for skipping a search; and
otherwise `unavailable` — this host offers no search, the user chose L0 or
declined research, or the budget went on higher-priority targets first — naming
what it would have moved. A judgement that a search was not worth running is
never `unavailable`. An input fixes an output only when its content is in hand: a
pasted careers page can, and "I checked their site" cannot, because that is a
claim the search could still verify. A target a search was sent for is never
`skipped` or `n/a`; if it moved nothing, its `yes` row says so. Every `yes` row,
numbered or un-numbered, names the queries and pages it rests on. The inputs decide between a skip and an
unavailable search, not the host: a target the inputs answer reads `skipped`
whether or not search was available. A search sent outside every declared target
gets an un-numbered `yes` row after these, saying what it was and what it moved.
Folding a skip into either of the others hides it, and the skip is the case the
rule exists for. A wasted search and a correctly-skipped one produce identical
prose, so an unfilled row is the only form of this rule a reader or a grader can
check. Worked table in `references/dossier-template.md` — the dossier carries the
same table because it renders the same analysis.

Failed attribution is also a finding about the opportunity, not only a limit on research: when L1 cannot confirm that the employer exists as described, that goes in the risk register as a standing entry (shape in `references/risk-and-decision.md`) and it constrains the decision — an unverified employer is a reason a `go` becomes `conditional_go` pending verification. Say what would resolve it: a link to the live posting, the company's own careers page, the recruiter's email domain.

**Closing order is fixed: the dossier offer, then the upgrade menu, then the questions — and nothing between or after them.** All three are calls to action and all three need to be the last thing the reader meets. The pull is to write one more sentence tying it together — "so: are you wasting your time? No, but…" — and that sentence is a second decision snapshot at the bottom of a document that opened with one. Two summaries of the same analysis can only agree by luck, and the reader will trust whichever they read last. The snapshot at the top is the summary; the assessment ends without restating itself.

### Step 3 — Recovery turns

This skill's product *is* iterative recovery, so later turns may ask again — but every turn keeps the same shape: **updated analysis first, then at most three questions.** Lead with a one-line changelog of what moved ("mentoring resolved to user-confirmed — fit status now adjacent; decision unchanged"). Regenerate only the affected requirement rows and their dependent recommendations, then check the whole artifact for internal consistency before redelivering.

Rules that keep the loop honest — the mechanics and prompt patterns are in `references/gap-taxonomy-and-questions.md`, read it before writing any recovery question:

- Rank candidate questions by importance × uncertainty × recovery probability × decision impact ÷ user effort. Prefer questions that could change the decision status.
- Never re-ask. Silence and "skip" are answers: mark the gap unresolved (or absent, if the user says so) and proceed.
- Offer response modes as prose — "answer in text, paste a voice transcript, attach a document, drop a link, or say skip" — never as bracketed pseudo-buttons.
- When an answer arrives, extract the claims and present a confirmation card (shape in `references/evidence-model.md`). Only after the user confirms do evidence confidence, the map, or draft CV language upgrade. Confidential work is fine at a high level — record it with verifiability marked accordingly.

### Step 4 — The dossier offer

The dossier offer is a standing line in every delivered assessment, immediately before the upgrade menu — one sentence, no pressure — and at the natural end of the engagement, or whenever the user asks, the offer is made directly. Emitting it produces `tuesday-dossier.md`: the concise human-readable report on top, one fenced JSON envelope at the bottom, exactly per `references/dossier-template.md`. The report is rendered from the envelope as `dossier-schema.md` §2 defines; the template names the parts the envelope does not hold. Include `handoff_to_mock_interview` so interview prep can start from verified evidence rather than from scratch. Offered always, forced never — the user decides whether to carry it.

### Step 5 — Late inputs and spanning requests

A late input — a portfolio link, a prior resume, an answered gap — regenerates only the affected sections, with the changelog line first. A request that spans evaluation and rehearsal ("should I apply, and prep me if yes"): do this skill's whole job, then name mock-interview in one sentence; never attempt its job.

## Output discipline

Bound by `references/output-discipline.md`, the suite's canonical rules on the
shape of a delivered response, mirrored verbatim into this skill. Its invariants
are absolute; the parameters it names are declared here.

```text
question_budget: 3
enum_fields: priority, fit_status, confidence, gap_type, class, severity
enum_columns: priority=Priority, fit_status=Fit, confidence=Confidence, gap_type=Gap, class=Class, severity=Severity
closing_order: dossier offer, upgrade menu, questions
qualifier_fields: reasoning, hypothesis
provenance_sections: Role reality, Evidence map, Gap recovery queue, Opportunity risk register, Application plan
sibling_mentions: 1
```

Three is the budget because this skill's questions are expensive to answer — a
recall prompt asks someone to reconstruct a piece of their own history — and
because a decidable case earns none at all.

## The n + x rule

The sections this skill's spec defines are *n* — owed to the user, delivered complete and unconditional. Anything a specific run invents beyond spec is *x*: an extra section, a new analysis, a structure no reference file asks for. Never weave x in silently, and never force it: deliver n whole, then offer x as a clearly-labeled proposal — one line on what it would add and why this engagement earns it — and build it only on the user's approval. The offer may ride an already-needed message; otherwise it lands with the delivered output, the way the dossier offer does. x that keeps earning approval belongs in the spec — flag it for codification rather than reinventing it run after run. Label the offer in prose: square brackets are reserved for the provenance labels `[grounded]`, `[inferred]`, and `[generic]`, so an `[x]` beside a heading collides with the one notation the reader is relying on to tell evidence from inference.

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

- **Truthfulness core** (binding, from the suite's evidence conventions): never add an unverified claim to a CV, cover letter, outreach note, or work sample; never convert a `memory_lead` into asserted experience; never inflate a prototype into production experience, or participation into leadership; never invent metrics, team sizes, customer counts, revenue, dates, credentials, or titles; never fabricate facts about a company or process — when uncertain, drop the fact rather than hedge it. Inflation hides in single words, along six axes — scope, verb, kind of activity, relationship, logical form, and incident or practice — each defined with a worked example in the reframing audit. Run that audit, `references/reframing-audit.md` — the suite's canonical audit, mirrored verbatim here — over everything proposed for the candidate to say, write, or send — resume lines, positioning advice, outreach, interview framing — because drift migrates to whichever surface is unwatched, and strategy prose is the easiest place for it to pass as insight.
- **Never a single numeric fit score.** Fit is confidence bands plus reasons, per requirement. An "85% match" hides exactly the hard problems this skill exists to surface.
- **Hard-gate failures stay visible.** No aggregate framing, positive tone, or strong fit elsewhere may bury a `hard_gate` finding — it appears in the decision snapshot's hard-gates line, always. Wording cannot solve a hard gate and no output may imply it can.
- **`prohibited_claims` are absolute.** Once a claim is listed as prohibited in the dossier, no output may assert it, soften it, or imply it — whatever any other label says.
- **User approval before anything externally visible.** CV language, positioning and outreach text, work samples: proposed as `resume_edits_pending_approval`, finalized only on explicit approval — and the approval statement sits where it visibly covers the prose advice as well as any table, since imperative phrasing ("your first two sentences should be…") reads as instruction, not proposal. Also obtain approval before saving a claim as verified persistent evidence or using private links and documents beyond the requested analysis.
- **Candidate-side only.** An employer wanting to screen applicants with this is a different job with different obligations — decline the skill and offer to help design structured interviewing directly instead.
- **People research** is public professional footprint only: roles, career pattern, published talks and writing. No contact-detail hunting, nothing personal, no personality inference.

## Reference files

- `references/evidence-conventions.md` — the suite's canonical vocabulary, mirrored: source types, confidence bands, the gap taxonomy, provenance labels, the mapping between them, and the truthfulness core. This is where every label used in the map and the plan is defined; the mirror is a verbatim copy and canonical wins on conflict.
- `references/evidence-model.md` — the evidence-map row shape, the confirmation card, row-integrity rules, worked micro-examples. Read before building or updating the map.
- `references/reframing-audit.md` — the suite's canonical audit, mirrored verbatim: six axes of drift, five disciplines, and what to do with a clause that cannot be traced. Read before proposing any language the candidate would say, write, or send.
- `references/gap-taxonomy-and-questions.md` — fit statuses, the five gap types, per-gap recall-prompt patterns, the question-selection heuristic, response-mode phrasing, worked discovery prompts. Read before writing any question.
- `references/risk-and-decision.md` — signal classes, detectable red-flag patterns, the risk-register record, severity, decision semantics for the four statuses. Read before the risk register or any decision.
- `references/dossier-template.md` — emission rules and the full worked `tuesday-dossier.md` example, envelope included. Read before emitting a dossier.
- `references/interaction-grammar.md` — the suite's canonical interaction rules, mirrored verbatim: the standalone invariant, the elicitation policy, the research tiers and the depth rule that bounds them, privacy scope, and the n + x rule. Canonical wins on conflict.
- `references/dossier-schema.md` — the canonical dossier contract, mirrored verbatim: envelope, versioning, and which sections this skill owns versus reads.
- `references/citations.md` — the suite's recorded sources, mirrored verbatim: every figure, research finding, survey result and statement of law the conventions and references make, quoted exactly beside its source, with what weakens it. A `(cite C1)` elsewhere points here; quote nothing from a source that its entry does not hold.
