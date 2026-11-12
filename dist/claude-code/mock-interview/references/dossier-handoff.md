# The dossier: reading the handoff, writing the feedback

Tuesday's skills compose in any order or not at all. The dossier (`tuesday-dossier.md`) is how a candidate carries work between them without the skills coupling to each other: job-underwriter writes what it learned underwriting a role, mock-interview reads it and writes back what rehearsal exposed. Canonical rules live in `references/dossier-schema.md`, the mirrored schema; this file is the operative copy of what *this* skill does with it.

The invariant that outranks everything here: **the dossier is an enhancer, never a gate.** A pack built without one is a complete pack. Never ask for a dossier as a precondition, never degrade the pack into an advertisement for job-underwriter, and never imply the candidate did prep wrong by not having one. Mention in the upgrade menu what it would add — one line — and move on.

## Reading it — the intake check

At Step 0, check context and uploads for `tuesday-dossier.md` (or a pasted JSON envelope carrying `dossier_version`). If present, parse the envelope and consume the sections below. If the envelope's major version is higher than this skill knows (currently 1.x), say so plainly in the pack's Sources section and build standalone rather than guessing at renamed fields. Unrecognized sections are ignored, not errors — forward compatibility is the default posture.

What this skill reads, and what each section replaces:

| Section | What it gives the pack |
|---|---|
| `handoff_to_mock_interview` | The five rules below — the core of the handoff |
| `role_profile` | The JD equivalent: requirements with priority, inferred outcomes, unknowns. A dossier with this section satisfies the JD input tier, and its requirement text stands as the supplied JD's lines — a raising source as `references/question-rubric.md` defines one — while its `unknowns` and inferred outcomes are the underwriter's analysis and are not |
| `evidence_map` | Per-requirement candidate evidence with confidence and gap type — the fit snapshot's grading, and its evidence quotes the snapshot's evidence cells. `reasoning` is the underwriter's analysis: a bridge may cite it as a limit, never as something the candidate did |
| `verified_candidate_evidence` | The CV equivalent for elicitation purposes: user-confirmed claims, already graded. A dossier carrying it satisfies the CV input tier |
| `evidence_state` | Its `rejected_inferences` — claims the candidate already corrected — are entries in the prohibited list (template section 13), with the basis and honest form `references/question-rubric.md` gives them |
| `risk_register` | Unresolved opportunity risks; feeds reverse questions alongside `opportunity_risks_to_validate` |
| `decision` | Context only. A `no_go` is not this skill's business to relitigate — if the candidate is prepping anyway, prep them |

One writer per section: this skill **reads** job-underwriter's sections and never rewrites them. Corrections route to the owner — if rehearsal contradicts an evidence-map row, that belongs in `pack_feedback`, not in an edited row.

**A dossier shrinks Step 1, and often empties it.** Requirements and confirmed evidence are the two inputs the clarifying message normally chases; a dossier carrying `role_profile` and `verified_candidate_evidence` supplies both, so neither the JD nor the CV may be asked for — the skill's own rule against asking for what it can already derive applies with full force here. What a dossier never carries is round type and relationship to the interviewer, recruiter guidance, interviewer identity, and research-depth consent; those, and a gate the dossier leaves unsettled, are the only things a Step 1 message may cover (the list is `SKILL.md` Step 1's), and only when the user hasn't already said them. Everything else that would still sharpen the pack — the raw CV behind the confirmed claims, a portfolio artifact — belongs in the upgrade menu as an offer, never in a request. The distinction is not cosmetic: a request reads as something the candidate owes before the work is good, and two days before an interview that costs them attention they do not have.

## The five consumption rules

These are what a handoff actually buys. Each replaces guesswork with something the underwriter established.

1. **Verified evidence upgrades story-mapping to `[grounded]`.** Claims in `verified_candidate_evidence` are user-confirmed; guidance built on them is story-mapped and labeled `[grounded]`, not scaffolded as though the CV were absent. Watch the confidence caveat: an entry marked medium — confirmed, with limited inspectable proof — stays `[grounded]` but the guidance names the caveat, because a prober will find that seam — coach the candidate to volunteer the limit before it's extracted.

2. **`allowed_interview_strategy` constrains what guidance may coach.** For each entry in `uncertain_or_weak_areas`, the strategy is binding, not advisory:
   - `clarify` — the evidence may exist but wasn't established. Coach a question-shaped answer: quote any `verified_candidate_evidence` entry that speaks to this requirement itself, word for word — evidence that is merely nearby is the scaffold case, not a bridge — then an answer slot naming the requirement's own wording as the interviewer's probe, whose second branch allows the candidate never worked that way, and the honest "here's what I'd want to confirm about how you define it." Nothing about the candidate's past goes into the answer unless it is quoted or sits in the slot.
   - `bridge` — adjacent evidence exists. Coach the transferable case **with its limit named**, exactly as the underwriter framed it. A bridge that drops the limit becomes the inflation the suite forbids. The framing gives the limit and how to position it; it is never a fact about the candidate's past — a dossier's decision prose can summarise the candidate more broadly than any verified entry does — so every clause about what the candidate did still rests on a quoted entry.
   - `acknowledge_gap` — no credible evidence. Coach the plain acknowledgment plus a ramp plan. Never coach a bridge here; the underwriter already looked and found nothing, and inventing one live is how a candidate gets caught.
   - An answer slot (`references/question-rubric.md`) follows the same strategy: allowed on a `clarify` area, inside the named limit on a `bridge` area, and never on an `acknowledge_gap` area — a slot asking "if you did this, say how" about what the underwriter found absent reopens the bridge this rule closes.

3. **`likely_interviewer_objections` names the highest-ROI rehearsal.** The rubric normally asks you to infer the most predictable objection from the fit snapshot. When the underwriter named it, use theirs — it was derived from evidence the candidate confirmed, not from a document read cold. Give it the deepest rehearsal in the pack and say in the pack that the underwriter named it. Word its Question under the premise rule in `references/question-rubric.md` ("What a question may presuppose"), which says when a negative in it may be kept.

4. **Risks and employer questions seed the reverse-question bank.** `opportunity_risks_to_validate` and `questions_for_employer` arrive interview-ready. Carry them into the reverse-question section with their "why it lands" written from the risk's own hypothesis — these questions do double duty: they read as diligence, and they answer something the candidate genuinely needs to know before accepting.

5. **`prohibited_claims` are hard guardrails on every guidance cell.** Absolute, and they beat every other label in this skill. No question's guidance, no values-story mapping, no reverse question, no answer slot, and no drill feedback may assert a prohibited claim, soften it, or coach an answer that implies it — and a slot that names one implies it. When a question's natural answer would brush one, coach the honest alternative and say why the line exists — a candidate who understands the boundary holds it under follow-up pressure.

Say in the pack's Sources section that a dossier was consumed and which sections it supplied, so the candidate can see which parts of the pack rest on their own confirmed evidence versus the pack's inference.

## Writing back — `pack_feedback`

Preparation exposes things underwriting cannot: what happens when the candidate tries to *tell* the story out loud. That is genuinely new information, and the dossier's reverse channel exists to carry it back.

Offer to emit or update the dossier with a `pack_feedback` section at the end of a pack, and again after any drill — one line, no pressure, same posture as the Word-conversion offer. Emit it only if the candidate wants it.

```yaml
pack_feedback:
  surfaced_objections: []        # objections the fit snapshot or drills exposed
  rehearsal_gaps:
    - requirement: string        # where the candidate had no credible story
      observed_in: fit_snapshot | drill
      suggested_gap_type: presentation | discovery | transferability | capability
  new_evidence_leads: []         # stories told in prep that the CV doesn't carry
```

Rules for writing it honestly:

- **`suggested_gap_type` is a suggestion, and the field name says so.** The underwriter owns classification; this skill proposes from what it saw. A story the candidate told fluently but that never reached the CV is `presentation`; a blank where a story should be is `discovery` before it is ever `capability` — one bad rehearsal is not evidence of absent capability, and calling it that in a file the candidate carries around does real harm.
- **`new_evidence_leads` are leads, not evidence.** Anything the candidate said mid-rehearsal is a self-report made under practice pressure. Record it as a lead for the underwriter to verify. Never phrase it as established, and never let a lead you recorded feed back into this same pack's guidance as though it were confirmed.
- **Nothing personal.** Rehearsal reveals nerves, hesitation, and self-doubt. None of that belongs in a file the candidate carries between sessions and may hand to a tool later. Record requirements and stories, never assessments of the person.
- **Write only this section.** `pack_feedback` is this skill's only writable section. Carry every other section through unchanged, including sections this skill doesn't recognize. Its lines in the report on top are rendered from the JSON section (`dossier-schema.md` §2); this skill adds no report-only part.

When updating an existing dossier, preserve its envelope version and its other sections verbatim; when emitting a fresh dossier that carries only `pack_feedback` (the mock-interview-first ordering, where no underwriting has happened yet), fill `role` and `generated_by` from what this engagement knows and leave the underwriter's sections absent rather than stubbed — an absent section is honest, an empty one invites a consumer to think it was assessed.
