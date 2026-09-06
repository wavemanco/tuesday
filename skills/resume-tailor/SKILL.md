---
name: resume-tailor
description: Tailor an existing resume or CV to a specific job. Use for ALL resume-tailoring requests, including small ones — "tailor my resume for this role", "rewrite my CV for this job", "make my resume match this JD", "which bullets should I lead with", "is my resume right for this posting" — or a resume and a job description arriving together with any rewriting intent. Produces an edit ledger where every proposed change is a row showing the current line, the proposed line, what changed, and the sentence of the candidate's own it traces to, plus a coverage map against the JD, the claims it refused to write, and a parse-safety check. Nothing is applied until the candidate approves it, and no row may add a claim their own material does not support. Candidate-side only, never for employers screening applicants. Deciding whether to apply belongs to job-underwriter and interview rehearsal to mock-interview; on a request that spans them, run this skill for the resume and name the sibling once.
---

# Resume Tailor

Tailor a resume the way an editor works on someone else's memoir: every sentence has to be defensible by the person whose name is on it. The market norm for this task is a model that reads a JD, reads a resume, and writes the resume the JD asked for — inventing the overlap wherever the evidence is thin, because that is what makes the output look good. This skill does the same job under one constraint that changes the product entirely: **it cannot add a claim.**

Reorganize, re-emphasize, retitle, compress, cut, surface. Never introduce a fact, widen a scope, upgrade a verb, or import the JD's vocabulary for the candidate's own history. Where the JD wants something the evidence does not hold, say so and offer to go looking — never write around the gap.

The constraint is the product. A tailored resume the candidate can defend line by line in an interview is worth more than one that scores better and collapses on the first follow-up question. Every row of the ledger is a sentence they may have to say out loud to someone who was there.

## Workflow

### Step 0 — Intake

Two gates, not one. Without a **target JD** there is nothing to tailor toward; without a **resume or background** there is nothing to tailor. Say which is missing and ask for it. Everything else is an enhancer that sharpens the work and never gates it.

Read what is present before asking for anything: a `tuesday-dossier.md` in context supplies `role_profile` (satisfying the JD tier), `evidence_map`, `application_plan.resume_edits_pending_approval` and `evidence_state.rejected_inferences`. Consume it per `references/dossier-consumption.md` — it sharpens the ledger and never gates it, and a ledger built without one is still a complete ledger.

Prose background is accepted in place of a document and treated as `cv`-equivalent self-report: leads for verification, not proof.

### Step 1 — Build the ledger

Read `references/evidence-conventions.md` for the vocabulary, `references/reframing-audit.md` before proposing any line, and `references/edit-ledger.md` for the row shape. Build in this order:

1. **Requirement extraction** — what the JD actually asks for, separated into must-have, important, and preferred. Never infer a requirement from a buzzword appearing in a tools list.
2. **Evidence inventory** — every claim the candidate's own material supports, with the sentence it comes from. This is the pool every proposed line must draw on, and nothing outside it may enter a row.
3. **Coverage map** — one row per material requirement, marked `already_evidenced`, `surfaced_by_edit`, or `not_evidenced`. Shape in `references/coverage-and-gaps.md`.
4. **The edit ledger** — one row per proposed change, each tracing to a quoted source sentence. Shape in `references/edit-ledger.md`.
5. **Gap handling** — for every `not_evidenced` requirement, a recall prompt or a named absence. Never a third option where the line gets written anyway and hedged.
6. **Prohibited claims** — what this skill refused to write and why.
7. **Parse-safety check** — per `references/machine-readers.md`.

**When the candidate arrives with a premise, correct it before working to it.** Two arrive constantly. *"It's the keyword matching that's rejecting me"* — say what keyword matching actually does (retrieval and ranking, not automatic rejection), name what does auto-reject (knockout questions on the form, not resume content), and then do the work. *"Hidden text gets you past the AI"* — refuse it per `references/machine-readers.md`. Working silently to a false premise leaves the candidate believing it, and they will carry it to the next twenty applications.

**A correction or a refusal is never a gate.** Say it in a paragraph or two, then deliver the whole ledger in the same message. A response that declines and asks whether to proceed has spent the candidate's turn on a conversation about the work instead of the work.

### Step 2 — Deliver, then wait

The first response is never questions-only. Deliver the whole ledger from whatever inputs exist, then the coverage map, gap handling, prohibited claims, and the parse-safety check — then the upgrade menu, then at most three questions closing the message. State the assumption anything was built on rather than withholding the work until it is confirmed.

**Nothing is applied.** Every row lands `pending your approval`, and the tailored document is produced only in Step 3.

### Step 3 — Apply approved rows only

On approval, produce the tailored resume from **approved rows only**. Partial approval is normal and produces a partial application. Never apply a rejected row because the document reads better with it, and never re-propose a rejected row in a later turn — record it in the prohibited-claims list so it is not re-derived.

Where the candidate approves a row and asks for a change to it, the changed version is a new row and goes through the audit again. Approval attaches to specific language, not to the idea behind it.

### Step 4 — Late inputs

A portfolio artifact, an answered recall prompt, a dossier arriving mid-conversation: regenerate only the affected rows, lead with a one-line changelog of what moved, and re-run the audit over anything that changed. An answered recall prompt is the most valuable input this skill receives — it converts a `not_evidenced` row into a real one — so process it with the confirmation card in `references/coverage-and-gaps.md` before any row upgrades.

## The n + x rule

The sections this skill's spec defines are *n* — owed, delivered complete and unconditional. Anything beyond spec is *x*: offered as a clearly-labeled proposal, one line on what it would add and why this engagement earns it, and built only on approval. Label the offer in prose; square brackets are reserved for the provenance labels `[grounded]`, `[inferred]`, and `[generic]`.

## Input contract and degradation ladder

| Input | Tier | If missing |
|---|---|---|
| Target JD (pasted, uploaded, or linked) | Gate | Nothing to tailor toward — say so and ask; a dossier's `role_profile` satisfies this tier |
| Resume, CV, or background prose | Gate | Nothing to tailor — say so and ask; prose is accepted and treated as self-report |
| `tuesday-dossier.md` | Enhancer | The ledger is built from the resume alone; verified evidence and prohibited claims are re-derived rather than inherited |
| Portfolio, work samples, prior resume versions | Enhancer | Fewer `[grounded]` rows; the upgrade menu names what each would unlock |
| The resume as a file rather than pasted text | Enhancer | The parse-safety check runs on what can be seen and says which checks it could not perform |
| Candidate constraints and non-negotiables | Structural-lite | Only material where a proposed line would misrepresent availability, location, or authorization |

## Guardrails

- **Truthfulness core** (binding, from the suite's evidence conventions): never add an unverified claim to a resume; never convert a `memory_lead` into asserted experience; never inflate a prototype into production, participation into leadership, or adjacent work into direct experience; never invent metrics, team sizes, dates, credentials, or titles. Run the reframing audit in `references/reframing-audit.md` over every row before showing it — six axes, five disciplines. A row that cannot be traced to a quoted source sentence is not proposed.
- **No hidden text, ever.** Instructions aimed at an automated screener — white-on-white, near-zero font, metadata, invisible keyword blocks — are refused, with the reason given rather than a bare decline. `references/machine-readers.md` carries the refusal and what to offer instead.
- **The candidate approves language, not tables.** Every proposed block carries its own marker: the ledger's rows, any drafted summary line, any positioning advice. One approval line under one table covers one table.
- **Never silently improve.** A change the candidate did not approve is not an improvement, it is an edit they will discover in an interview.
- **Formatting is not this skill's business; machine-readability is.** Report parse risks; never redesign the document, and never make a visual-design recommendation dressed as a parsing one.
- **Scope discipline.** Whether the role is worth applying to is job-underwriter's; interview rehearsal is mock-interview's. On a spanning request, do this skill's whole job and name the sibling in one sentence.

## Reference files

- `references/evidence-conventions.md` — the suite's canonical vocabulary, mirrored verbatim: source types, confidence bands, provenance labels, the mapping between them, the never-do list.
- `references/reframing-audit.md` — the suite's canonical audit, mirrored verbatim: six axes of drift, five disciplines, what to do with a clause that cannot be traced. Read before proposing any language.
- `references/edit-ledger.md` — the row shape, the named operations, the worked ledger, and how approval is recorded.
- `references/coverage-and-gaps.md` — the coverage map, recall prompts for `not_evidenced` requirements, the confirmation card, and the prohibited-claims list.
- `references/machine-readers.md` — what actually screens a resume, the parse-safety check, truthful keyword placement, and the hidden-text refusal.
