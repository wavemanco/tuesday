<!-- SYNCED FROM: conventions/dossier-schema.md
     Canonical wins on conflict. Everything below this comment block is a
     verbatim copy of the canonical file — do not edit it here. Fixes flow
     canonical -> mirror, never the reverse; a mirror that drifts is a defect.
     A byte check strips this header and compares the remainder to canonical. -->
# Dossier schema

## Contents

- 1. Behavior contract
- 2. Carrier format
- 3. Versioning
- 4. Envelope (v1.2)
- 5. Sections — owner and consumers
- 6. `handoff_to_mock_interview` (v1.0)
- 7. `pack_feedback` (v1.0)
- 8. UI note
- 9. Version history

The dossier is Tuesday's shared artifact: one file the user carries between skills, sessions, and — later — the agent. It makes the skills order-independent without coupling them. Skills carry a mirror of this file in their `references/` with a synced-from header; on a conflict between a mirror and the canonical file it names, the canonical file wins.

## 1. Behavior contract

- **Read-if-present.** Every skill checks whether a dossier is in context or uploads. If present, consume the sections relevant to your job. If absent, run standalone — the dossier is an enhancer, never a gate (see `interaction-grammar.md` §1).
- **Append-always-offered.** Every skill offers to emit or update the dossier at the end of its work. The user decides whether to carry it.
- **One writer per section.** Each section has exactly one owning skill; consumers read, never mutate. Corrections route through the owner.
- **Tolerate the unknown.** Skills must tolerate missing sections and ignore unrecognized ones — forward compatibility is the default posture.
- **Transport reality.** Within one conversation the dossier lives in context. Across conversations, the user re-uploads the file. There is no shared filesystem between skills; the dossier is one file precisely because of that.

## 2. Carrier format

A single Markdown file, `tuesday-dossier.md` — named so it stays recognizable among a user's uploads across sessions — with a concise human-readable report on top and the machine layer as one fenced ```json block at the bottom. Two layers, one artifact, no drift — every report line whose content a JSON field holds is rendered *from* that field, never written separately. A report part no JSON field holds is report-only: the emitting skill's dossier template names each such part, it is carried as the delivered output wrote it, no later skill reads it, and it never restates what the JSON holds — where it needs a fact the JSON carries, it points to the row or entry ("see R8") instead.

## 3. Versioning

- The JSON envelope carries `dossier_version` (this document defines `1.2`; history in §9).
- Additive changes (new optional fields, new sections) bump the minor: `1.1`. Consumers ignore what they don't know.
- Breaking changes (renamed/removed fields, changed semantics) bump the major and require a migration note appended to this file in the same change.
- A skill reading a higher major than it knows says so and proceeds standalone rather than guessing.

## 4. Envelope (v1.2)

```json
{
  "dossier_version": "1.2",
  "generated_by": { "skill": "job-underwriter", "at": "2026-08-15" },
  "role": {
    "title": "string",
    "company": "string | null",
    "stage": "evaluating | applying | interviewing | offer"
  },
  "sections": { }
}
```

## 5. Sections — owner and consumers

| Section | Owner | Consumers | Contents (summary) |
|---|---|---|---|
| `role_profile` | job-underwriter | mock-interview, resume-tailor* | Title, responsibilities, requirements with priority, inferred outcomes, unknowns |
| `candidate_constraints` | job-underwriter | all | The candidate's constraints and non-negotiables: `status` (`known` or `unknown`); `items[]` each with the constraint text, `kind` (`hard` or `preference`), evidence `source`, and `satisfied_by_role` (`yes`, `no`, `unknown`) |
| `evidence_map` | job-underwriter | all | Per material requirement: priority, fit_status, candidate_claim, evidence[] (source_type + reference + quote_or_summary), verified, confidence, gap_type, reasoning, provenance, next_action — vocabulary per `evidence-conventions.md` |
| `gap_queue` | job-underwriter | — (user-facing) | The 1–3 highest-value unresolved gaps with tailored recall prompts and response modes |
| `risk_register` | job-underwriter | mock-interview | Signal, severity, source quote, hypothesis, verification question, status |
| `application_plan` | job-underwriter | resume-tailor* | `resume_edits_pending_approval`, work-sample suggestion, research actions |
| `evidence_state` | job-underwriter | all | Verified facts, unverified leads, rejected inferences |
| `decision` | job-underwriter | — (user-facing) | `go / conditional_go / hold_pending_answers / no_go`, rationale, hard gates, severe red flags — never a numeric score |
| `handoff_to_mock_interview` | job-underwriter | mock-interview | See §6 |
| `pack_feedback` | mock-interview | job-underwriter | See §7 — the reverse direction |

*resume-tailor: planned third skill; listed so its seams are reserved, not because it exists.

## 6. `handoff_to_mock_interview` (v1.0)

```yaml
handoff_to_mock_interview:
  high_priority_requirements: []        # the requirements interviews will actually test
  verified_candidate_evidence: []       # high/medium-confidence claims, per `evidence-conventions.md` §5
  uncertain_or_weak_areas:
    - requirement: string
      gap_type: discovery | transferability | capability
      confidence: low | none
      allowed_interview_strategy: clarify | bridge | acknowledge_gap
  likely_interviewer_objections: []     # nominates the pack's highest-ROI rehearsal
  opportunity_risks_to_validate: []     # unresolved risk-register items worth asking about live
  questions_for_employer: []            # seeds reverse questions
  prohibited_claims: []                 # absolute — see `evidence-conventions.md` §5 overrides
```

Consumption rules for mock-interview (bound in its v2 patch): verified evidence upgrades story-mapping to evidence-level `[grounded]`; `allowed_interview_strategy` constrains what guidance may coach; `likely_interviewer_objections` names the highest-ROI rehearsal instead of inferring it; risks and employer questions seed the reverse-question bank; `prohibited_claims` are hard guardrails on every guidance cell.

## 7. `pack_feedback` (v1.0)

The reverse handoff, for the mock-interview-first ordering:

```yaml
pack_feedback:
  surfaced_objections: []        # objections the fit analysis or drills exposed
  rehearsal_gaps:
    - requirement: string        # where the candidate had no credible story in rehearsal
      observed_in: fit_snapshot | drill
      suggested_gap_type: presentation | discovery | transferability | capability
  new_evidence_leads: []         # stories the candidate told in prep that the CV doesn't carry
```

The underwriter treats `rehearsal_gaps` and `new_evidence_leads` as discovery inputs — leads to verify, never as verified evidence (they are candidate self-reports made mid-rehearsal).

## 8. UI note

Any review surface — a claude.ai artifact, a Cowork HTML viewer with feedback download, a human-review-style local editor in shell hosts — renders and edits **this JSON**, and returns decisions into it. The reasoning stays in the skills; the UI stays a renderer. One schema, N thin renderers per host.

## 9. Version history

- **1.0** — initial schema.
- **1.1** (2026-08-16, additive) — added the `candidate_constraints` section. Surfaced by job-underwriter v0.1's worked dossier: the underwriter's spec carries candidate constraints as a first-class object (non-negotiables drive hard-gate checks and the risk register), and constraints must travel in the dossier or every new session re-elicits them. Consumers on 1.0 ignore the unknown section, per §1.
- **1.1 erratum** (2026-09-08, no version change) — `gap_type` has six members, not five: `evidence-conventions.md` §3 omitted `none` while the emitting skill's row spec declared it, the worked dossier wrote it, and every 1.1 envelope has carried it. Nothing on the wire changes, so nothing is bumped; a consumer that implemented five was reading a documented contract narrower than the emitted one. Recorded here rather than silently corrected because the gap between the two is what a version history is for.
- **1.2** (2026-09-08, additive) — `evidence_map[].provenance`, `risk_register[].provenance` and `gap_queue[].provenance`. All three carry free-text fields holding derived judgment — `reasoning` and `hypothesis` — and neither had a label beside it, so the largest concentration of world-claims in a dossier travelled unmarked. Found by graders pointing at those exact cells across a run-set, after the same defect had been fixed once in the register and missed in the map. Consumers on 1.1 ignore the unknown fields, per §1.
