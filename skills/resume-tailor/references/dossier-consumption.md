# Consuming `tuesday-dossier.md`

A dossier is a gift and never a dependency. Everything below sharpens the ledger;
nothing below gates it. A tailoring run with no dossier is a complete tailoring
run, and the upgrade menu is where the difference gets named rather than felt.

The schema is `conventions/dossier-schema.md`. This skill is a **consumer only**:
it reads and never writes. Writing back would need a new section and a version
bump, and v0 has not earned one.

## What to read, and what it changes

| Section | What it gives this skill |
|---|---|
| `role_profile` | Satisfies the JD gate outright — title, responsibilities, requirements already separated by priority, hard gates, unknowns. With one in hand, the JD is not asked for and drops to an upgrade-menu line |
| `evidence_map` | The strongest input available. Rows already carry the claim, its source quote, `verified`, `confidence` and `gap_type` — so a ledger row's trace cell can quote an evidence row instead of re-deriving it from the resume |
| `application_plan.resume_edits_pending_approval` | Edits the underwriter already drafted and the candidate has not yet approved. **Consume these; do not re-derive them** |
| `evidence_state.rejected_inferences` | Inferences the candidate has already corrected. These go straight into the prohibited-claims list, unaltered |
| `candidate_constraints` | Only material where a proposed line would misrepresent availability, location, or authorization |
| `decision` | Read it, act on none of it. Whether to apply is not this skill's question — but a `no_go` is worth one sentence, because tailoring a resume for a role the underwriter rejected is worth flagging before the work, not after |

## Five rules for consumption

- **An inherited edit is still audited.** A row arriving from `resume_edits_pending_approval` goes through the reframing audit exactly like a locally-derived one. The underwriter's audit ran against its own evidence map at its own moment; the resume may have changed, and a row that traced then may not trace now.
- **Never re-derive what the dossier already settled.** If `evidence_map` marks a requirement `adjacent` with a `transferability` gap, the coverage map inherits that judgment rather than forming a fresh opinion. Two skills disagreeing about the same evidence in the same conversation is the failure the dossier exists to prevent.
- **`rejected_inferences` are absolute.** Not a caution, not a preference. A claim the candidate has already rejected does not re-enter through a different phrasing, and the prohibited-claims list carries it with its original reason.
- **Confidence transfers; it does not upgrade.** A `medium` row in the evidence map is a `medium` row here. Tailoring does not verify anything, so nothing gets stronger by being written into a resume — if anything, a claim about to be published deserves the more conservative reading.
- **A stale dossier is worse than none, and says so.** Where the dossier's `role_profile` names a different role than the JD in front of you, or the resume has clearly changed since, say which parts you are using and which you are ignoring. Silently blending two versions of a candidate's history is how a resume acquires a line neither source supports.

## When there is no dossier

Build the same structures from the resume and JD directly. The coverage map is
derived rather than inherited, the prohibited-claims list is built from what the
JD invites and the resume cannot support, and every ledger row traces to the
resume's own sentences.

The one honest difference: with no dossier, nothing has been *verified* — the
resume is self-report, so rows are `[grounded]` in the document rather than in
confirmed evidence, and the upgrade menu should say what running job-underwriter
first would add. Say it once, as an offer, and get on with the work.
