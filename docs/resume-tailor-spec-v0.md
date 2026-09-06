# resume-tailor — spec v0

**Status: proposed, not approved.** job-underwriter was built against a spec and
a build brief the maintainer supplied. No equivalent exists for this skill, so
this document is the author's design rather than the maintainer's contract, and
it is deliberately reviewable before any skill file is written. Where it is
wrong, it is wrong on paper and costs a paragraph to fix.

What the repository already commits to, and what this spec must therefore honour:

- The README: *"evidence-locked resume tailoring — consumes verified evidence and prohibited claims; the showcase for the human-review UI pattern."*
- `conventions/dossier-schema.md` §5 reserves two seams, both with resume-tailor as **consumer**: `role_profile` and `application_plan` (which carries `resume_edits_pending_approval`).
- The one rule: the skill runs to a complete, useful output from a resume and a JD alone. A dossier sharpens it and never gates it.

## 1. What it is for

A candidate has a resume and a specific role. The resume was written for a
different audience, or for no audience. Tailoring it is the most common task in
a job search and the one where every available tool is willing to lie: the
market norm is a model that reads a JD, reads a resume, and writes the resume
the JD asked for — inventing the overlap where the evidence is thin, because
that is what makes the output look good.

This skill does the same job under a constraint that changes the product: **it
cannot add a claim.** It may reorganize, re-emphasize, retitle, cut, and reframe
within what the candidate's own words support. It may not introduce a fact,
widen a scope, upgrade a verb, or import the JD's vocabulary for the candidate's
history. Where the JD wants something the evidence does not hold, the skill says
so and offers to go looking — it never writes around the gap.

That constraint is the product. A tailored resume the candidate can defend line
by line in an interview is worth more than one that scores better and collapses
under a follow-up question.

## 2. The owed output (*n*)

Delivered complete in the first response, from whatever inputs exist.

### 2.1 The edit ledger — the centrepiece

Not a rewritten document. A per-change proposal table, because the candidate
approves changes, not a diff they have to reverse-engineer.

| # | Section | Current line | Proposed line | What changed | Traces to | Provenance | Status |
|---|---|---|---|---|---|---|---|

- **What changed** names the operation in the audit's own vocabulary: reorder, surface, cut, retitle, compress, split, reframe. Not "improved".
- **Traces to** quotes the candidate's own source sentence — from the resume, an attachment, or a dossier's `evidence_map`. A row whose trace cell would be empty is a row that does not get proposed.
- **Provenance** is `[grounded]`, `[inferred]`, or `[generic]`, in its own column. Structural, for the reason `evidence-model.md` gives: three prose rules failed to keep these labels attached, and an empty cell is visible where a missing suffix is not.
- **Status** is `pending_approval` on delivery. Nothing is applied until the candidate approves it.

### 2.2 The coverage map

One row per material JD requirement: what the JD asks, what the current resume
evidences, and what the proposal does about it — `already_evidenced`,
`surfaced_by_edit`, `not_evidenced`. The third value is the honest one and must
not be quietly absent: a requirement the resume cannot support appears in the
map saying so, with the recovery move (§2.3) attached.

### 2.3 The gap handling

For every `not_evidenced` requirement, exactly one of:

- **A recall prompt** — the discovery pattern, in the shape job-underwriter uses: the requirement, what the resume currently shows, experience that may count, evidence worth attaching, one question, response modes as prose.
- **A named absence** — where the evidence genuinely is not there, said plainly, with what closing it would take.

Never a third option in which the line is written anyway and hedged.

### 2.4 The prohibited-claims list

Explicit, and carried in the output. With a dossier: `evidence_state.rejected_inferences`
plus anything the map marks unverified. Without one: built from the resume
itself — claims the JD invites that the resume cannot support. The list exists so
the candidate can see what this skill refused to write, which is the part of the
work that would otherwise be invisible.

### 2.5 The tailored resume

Produced **only on approval**, and only from approved rows. Partial approval is
normal and produces a partial application — the skill never applies a rejected
row because the document reads better with it.

### 2.6 Upgrade menu

Each missing input and what it unlocks: the JD text, the current resume as a
document rather than pasted prose, a portfolio artifact, a `tuesday-dossier.md`.

## 3. Explicit non-goals

- **Not a decision.** Whether to apply belongs to job-underwriter. If the request is "should I apply and tailor my resume", this skill does the tailoring and names the sibling once.
- **Not interview preparation.** That is mock-interview.
- **Not formatting or design.** Length, layout, and typography are not this skill's job; it operates on claims. It may note that a two-page resume is long, once, and move on.
- **Not ATS keyword stuffing.** Keywords appear only where the evidence already supports them. A keyword the evidence does not support is a prohibited claim wearing a technical justification.

## 4. Inputs and degradation

| Input | Tier | If missing |
|---|---|---|
| Target JD | Gate | Cannot tailor without a target; say so and ask |
| Current resume or background prose | Gate | Cannot tailor a document that does not exist; prose background is accepted and treated as `cv`-equivalent self-report |
| `tuesday-dossier.md` | Enhancer | `evidence_map` and `application_plan.resume_edits_pending_approval` sharpen the ledger; without one the skill builds its own from the resume |
| Portfolio artifacts, prior resume versions | Enhancer | Fewer `[grounded]` rows; upgrade menu says so |
| Candidate constraints | Structural-lite | Only relevant where a proposal would misrepresent availability or location |

Two gates rather than one is a deliberate departure from job-underwriter, which
gates only on the JD. Tailoring needs both sides; there is no useful degraded
output from a JD alone that is not simply job-underwriter's job.

## 5. Bound by the suite

- **Vocabulary** from `conventions/evidence-conventions.md`, mirrored verbatim into the skill: source types, confidence bands, provenance labels, the mapping, the never-do list.
- **The reframing audit** governs every proposed line. See §7 — it needs to move.
- **Interaction grammar**: standalone invariant, elicitation policy, response modes as prose, n + x, trigger hygiene.
- **Dossier**: consumer only in v0. Writing back would need a new schema section and a version bump, and v0 does not earn one.

## 6. Triggering

Reserved phrasings: "tailor my resume for this role", "rewrite my CV for this
job", "make my resume match this JD", "which of my bullets should I lead with",
a resume and a JD arriving together with a rewriting intent.

Boundary, for `conventions/interaction-grammar.md` §6: **owns** tailoring an
existing resume to a named target; **not for** deciding whether to apply, and
**not for** interview preparation.

Routing consequence, already recorded in the ledger: a third skill makes every
existing routing case ambiguous again. This skill ships with its own positives,
its own near-miss negatives, and a re-run of the whole set — not a re-run of its
own cases only.

## 7. The one conventions change this needs

**The reframing audit should be promoted to `conventions/`.** It currently lives
in `skills/job-underwriter/references/gap-taxonomy-and-questions.md`, and it is
not job-underwriter's property: it governs *any* language a Tuesday skill
proposes a candidate say, write, or send. resume-tailor is the skill where it
matters most — every row of the edit ledger is exactly the artifact the audit
exists to police.

Copying it into resume-tailor would create the drift the mirror system exists to
prevent: two divergent copies of six axes and five disciplines, in the two places
they are load-bearing.

Proposed: a new canonical file `conventions/reframing-audit.md`, mirrored
verbatim into both skills behind the standard synced-from header, with
job-underwriter's copy replaced by the mirror. This is a conventions change and
therefore the maintainer's call, not the author's. **The skill is buildable
without it** — v0 can ship reading job-underwriter's copy as its source of truth
and carrying a pointer — but that arrangement is worse, and it is worse in the
specific way the repository already names as a defect.

## 8. Evals

Four fixtures, each carrying a trap the skill must not fall into:

1. **The strong-overlap resume.** Genuine fit; the temptation is to gild. Tests that reorganization stays traceable and that no line acquires scope it did not have.
2. **The pivot resume.** The JD's must-have is adjacent, not direct. Tests that the gap surfaces as `not_evidenced` with a recall prompt rather than being written around, and that adjacent work is not retitled into direct experience.
3. **The dossier-driven run.** A `tuesday-dossier.md` with `prohibited_claims` and `rejected_inferences` present. Tests that prohibitions are honoured, that `resume_edits_pending_approval` is consumed rather than re-derived, and that the pack works if the dossier is absent.
4. **The keyword trap.** A JD dense with tooling the resume never mentions. Tests that keywords are not inserted for ATS reasons, that the absence is named, and that the skill does not offer a "technically true" phrasing.

Every fixture asserts the first-response completeness rule, the per-row trace
and provenance columns, and that nothing proposed for the candidate to say
survives the audit unsourced.
