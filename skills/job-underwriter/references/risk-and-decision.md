# Opportunity risk and the decision

The skill assesses the opportunity independently of the candidate's fit for it. These are two ledgers: the evidence map answers "can this candidate credibly do this role?", the risk register answers "is this role what it claims to be, and is it acceptable to this candidate?". A strong answer on one ledger never compensates for a weak answer on the other — the decision reports both, separately, and is never a blended average.

## Signal classes

| Class | Meaning | Output action |
|---|---|---|
| Unknown | Material information is missing, without evidence of harm | Ask a verification question; list in role reality's unknowns |
| Risk signal | Wording or structure plausibly indicates a problem | Add to the risk register; investigate at the consented research tier |
| Red flag | Terms or structure appear materially unreasonable, misleading, incompatible, or unacceptable to this candidate | Highlight prominently; may force `no_go` |
| Positive signal | Clear outcomes, authority, resources, transparency, realistic scope | Increase opportunity confidence; say so — the register is not only for bad news |

An unknown is not a risk signal, and a risk signal is not a red flag. Escalating a class without new evidence manufactures alarm; refusing to escalate when the evidence is there buries it. The quoted source language decides.

## Detectable patterns

Patterns worth actively checking every JD for — each detectable from the posting text or user-provided evidence alone:

- **Responsibility without authority or resources** — "own revenue growth" with no team, budget, or decision rights in sight.
- **Bundled specializations** — several full roles folded into one title, usually junior-priced.
- **Seniority-compensation mismatch** — years and mandate that the stated compensation doesn't buy at market; needs the L1 role-family sweep to confirm, a risk signal until then.
- **Always-on expectations** — explicit or winking ("evenings and weekends when it matters").
- **Evasive or contradictory terms** — compensation that dissolves into "upside", employment type that shifts between paragraphs, claims in tension ("profitable since day one" beside a fresh funding stage).
- **Absent success metrics on a demanding mandate** — accountability with no stated definition of success.
- **Incoherent or copied JD language** — internal contradictions, mismatched titles, boilerplate stitched visibly together.
- **Process inconsistencies** — only when visible from user-provided evidence (a recruiter's terms differing from the JD's); never inferred from nothing.

The candidate's stated non-negotiables extend this list per engagement: a role attribute that conflicts with one is a red flag for *this* candidate whatever the market thinks of it.

## The risk-register record

```yaml
signal: "Responsibility-authority mismatch"
class: unknown | risk_signal | red_flag | positive_signal
severity: low | medium | high            # for risk signals and red flags
source_quote: "Own revenue growth across ..."
hypothesis: "Candidate may be accountable without decision rights or resources."
verification_question: "Which revenue levers does this role directly control, and what people, budget, and authority are committed?"
decision_rule: "Proceed only if authority and resources are concrete and consistent across interviewers."
status: unresolved | reduced | confirmed
```

Every register entry carries a `verification_question` the candidate can ask a live interviewer verbatim — the register doubles as interview preparation, and unresolved entries feed `opportunity_risks_to_validate` in the mock-interview handoff. `severity: high` entries are the "severe red flags" the decision snapshot must carry.

## Decision semantics

`decision.status` is one of four values. What each one means, and when it applies:

| Status | Meaning | Applies when |
|---|---|---|
| `go` | Apply; the evidence supports it | No hard-gate failures; must-haves at `direct`/`adjacent` with reasonable confidence; no unresolved severe red flags |
| `conditional_go` | Apply, with named conditions | Fit and opportunity are sound *if* specific named things hold — a gap closes, a risk verifies clean in interviews. The conditions are listed, each tied to a requirement or register entry |
| `hold_pending_answers` | Don't decide yet | Open questions in the gap queue or register could genuinely change the status. The snapshot names *which* answers, so the user knows what the hold is waiting on |
| `no_go` | Don't pursue, or stop | A hard-gate failure with no factual path to resolution, a confirmed severe red flag, or capability gaps across multiple must-haves with no realistic closure |

Rules that bind the decision:

- **Hard-gate failures cap the status.** A failed gate means the status can be at most `hold_pending_answers` — and only when the gate itself might factually resolve (the employer flexes terms, the user revises a non-negotiable, an uncertain gate clarifies). A gate that is simply failed means `no_go`, stated with the gate as the reason, however strong the fit elsewhere.
- **Both ledgers appear in the rationale.** "Strong fit; poorly-scoped role" is two sentences, not one hedged sentence. A qualified candidate deserves to hear both truths.
- **`hold_pending_answers` is a real status, not a dodge.** It must name the specific answers it waits on; a hold with nothing named is an unfinished decision.
- **The user decides; the skill recommends.** The status comes with reasons and confidence language, never as a command. If the user proceeds against a `no_go`, the register travels with them — those verification questions just became essential.
- **Never a single numeric fit score.** The status plus per-requirement confidence bands *is* the answer to "how good a fit am I?". A percentage would average away exactly the hard gates and severe flags this file exists to keep visible.

## The decision snapshot

The snapshot leads every delivered assessment — concise decision first, inspectable detail after:

1. Status, in one line.
2. Rationale: both ledgers, two or three sentences.
3. Hard gates: every `hard_gate_fail`, plainly, or "none found".
4. Severe red flags: every `severity: high` register entry, or "none found".
5. What would change this: for `conditional_go` the conditions; for `hold_pending_answers` the awaited answers; for `no_go` the facts that would have to be different.

Regenerate the snapshot on every turn that changes the map or the register — a stale decision over fresh evidence is the inconsistency readers notice first.
