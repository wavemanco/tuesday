# Opportunity risk and the decision

## Contents

- Signal classes
- Detectable patterns
- Two standing entries
- The risk-register record
- Decision semantics
- The decision snapshot

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

- **Responsibility without authority or resources** — "deliver the new grants programme" with no team, budget, or decision rights in sight.
- **Bundled specializations** — several full roles folded into one title, usually junior-priced.
- **Seniority-compensation mismatch** — years and mandate that the stated compensation doesn't buy at market; needs the L1 role-family sweep to confirm, a risk signal until then.
- **Always-on expectations** — explicit or winking ("we're a family, and families pitch in after hours").
- **Evasive or contradictory terms** — compensation that dissolves into "rewards to match your impact", employment type that shifts between paragraphs, claims in tension ("an established team of twelve" beside "you will build the function from scratch").
- **Absent success metrics on a demanding mandate** — accountability with no stated definition of success.
- **Incoherent or copied JD language** — internal contradictions, mismatched titles, boilerplate stitched visibly together.
- **Process inconsistencies** — only when visible from user-provided evidence (a recruiter's terms differing from the JD's); never inferred from nothing.

The candidate's stated non-negotiables extend this list per engagement: a role attribute that conflicts with one is a red flag for *this* candidate whatever the market thinks of it.

## Two standing entries

These two are checked on every engagement rather than waiting to be noticed, because both were found to matter in every run and neither announces itself in the posting's language.

**Employer not established.** When L1 research cannot attribute the employer to a real entity matching the posting's description — name collisions, no web presence, a careers page with no such role — record it:

```yaml
signal: "Employer not established from attributable sources"
class: risk_signal
severity: medium          # high when combined with other flags: comp withheld, off-domain contact, urgency pressure
source_quote: "<the posting's own identifying language>"
hypothesis: "The entity may be too new or small to have a footprint, the posting may be stale or aggregated, or it may not represent a real hiring employer."
provenance: "[generic] pattern for companies of this size, not a claim about this one"
verification_question: "Can you point me at the role on your own careers site, and who would I be interviewing with?"
decision_rule: "Verify the employer exists and the posting is live before investing application effort."
status: unresolved
```

This caps the decision at `conditional_go` — "apply, once the posting verifies" — because effort spent on an unverified employer is the cheapest loss in the process to avoid. Say plainly what would clear it, and keep the severity proportionate: most small companies are simply small, and treating obscurity as fraud is its own failure.

**Market calibration.** Where the role-family sweep ran, place the role's title, seniority, and scope against role-family norms and carry the result into role reality, labeled `[generic]` — a pattern, never a claim about this employer. Stated compensation is calibrated against that band, and a gap wide enough to change the decision becomes the seniority-compensation mismatch entry above. Unstated compensation is calibrated too: the band still tells the candidate what to expect, and the withholding itself is worth one verification question. Two disciplines keep this honest — name the band's basis (what was searched, how recent), and never present a market band as this employer's offer.

## The risk-register record

```yaml
signal: "Responsibility-authority mismatch"
class: unknown | risk_signal | red_flag | positive_signal
severity: low | medium | high            # for risk signals and red flags
source_quote: "Lead the new fund from launch to its first awards ..."
hypothesis: "Candidate may be accountable without decision rights or resources."
provenance: "[inferred] from the JD's scope language against its silence on authority"
verification_question: "Which funding decisions does this role make itself, and what staff, budget, and authority are committed?"
decision_rule: "Proceed only if authority and resources are concrete and consistent across interviewers."
status: unresolved | reduced | confirmed
```

Severity is one value too — `low`, `medium`, or `high`. The same rule as the confidence bands applies and for the same reason: `severity: high` is what the decision snapshot must surface as a severe red flag, so a hybrid leaves the snapshot unable to decide whether the entry belongs there. When an entry sits between two, take the lower and put the reason in the hypothesis — over-stating severity manufactures the alarm this file warns against.

Every register entry also carries a `provenance` label on its `hypothesis`, for the reason the whole taxonomy exists: a hypothesis is a claim about the world — this employer, this market, how hiring works — and it is the claim in the register most likely to be quoted back without its basis. `[generic]` is the honest label for most of them, and writing `[generic]` where the pull is to write `[inferred]` is the discipline: "small companies often have thin footprints" is a pattern, not a finding about this company.

Every register entry carries a `verification_question` the candidate can ask a live interviewer verbatim — the register doubles as interview preparation, and unresolved entries feed `opportunity_risks_to_validate` in the mock-interview handoff. **Every** entry, not the standing ones that arrive with a worked example attached: the characteristic failure is a register rendered as a compact table whose columns stop at severity and source quote, so the entries carrying the actual red flags — the ones the candidate most needs a question for — are the only ones that lose it. An entry without a question the candidate could ask out loud is unfinished, and a table that cannot fit the column is the wrong shape for the register. The question is addressed to the employer, not to the candidate: "can you point me at the live posting" asks the candidate to go looking, which is a next action, not a verification question. `severity: high` entries are the "severe red flags" the decision snapshot must carry.

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
- **The user decides; the skill recommends.** The status comes with reasons and confidence language — confidence in the recommendation, never a band summarised over rows — never as a command. If the user proceeds against a `no_go`, the register travels with them — those verification questions just became essential.
- **Never a single numeric fit score.** The status plus per-requirement confidence bands *is* the answer to "how good a fit am I?". A percentage would average away exactly the hard gates and severe flags this file exists to keep visible.

## The decision snapshot

The snapshot leads every delivered assessment — concise decision first, inspectable detail after:

1. Status, in one line — **and where the user asked a direct question, the line answers it in their words before it names the status.** "No, you would not be out of your depth — `conditional_go`" answers what was asked; `conditional_go` alone answers a question nobody put. This is a reading of the map and carries no label, which is exactly why it belongs at the top: an answer the reader has to assemble from the tables is an answer that gets rewritten as a paragraph at the bottom, after the calls to action, where rule 4 says nothing but the watch-out line may follow and rule 6 says a world-claim needs a row. One run has already done it. Where the line's reason is about rows, it names them by ID, as every statement about a set of rows in the snapshot does (`references/evidence-model.md`, "The row is the unit"): "No — R1 and R2, both hard gates, fail · `no_go`" can be checked against the map, and "both of your hard constraints fail" cannot.
2. **Fit ledger** — the evidence map projected by row ID and read off the finished map: one line per Priority tier present, in enum order (`hard_gate`, `must_have`, `important`, `preferred`); on each line the rows grouped by Fit, in enum order (`direct`, `adjacent`, `unclear`, `absent`, `hard_gate_fail`), every map row exactly once, split rows (R4a, R4b) as rows, no ranges; and every row below `direct` followed by a few of its Requirement's own words in parentheses. Then at most one sentence on what matters, written as a list so that two readings stay one sentence: an item for each row, or group of rows, it reads, each item its row IDs, a dash and a few words, and the items separated by semicolons. Any set claim it makes is judged under the rule in `references/evidence-model.md` ("The row is the unit"), which reads every word of its lists and every ratio in this sentence as about the map, and scopes one more word to it. The first runs written to this shape put a false set claim exactly there: "R5b and R8 are the only rows below `direct`", directly under a ledger that listed a third. The worked snapshot in `references/dossier-worked-report.md` is the shape.
3. **Opportunity ledger**, one or two sentences, reading the register and naming the entry IDs it reads.
4. **Hard gates**, the bullet slot `- **Hard gates:** …`, in every snapshot, gate rows or not, read from the map's `hard_gate` rows. Every `hard_gate` row is named, with its fit, in every case, in this order: the `hard_gate_fail` rows first, after `failed:`; then the `unclear` ones, after `unconfirmed:`; each of those with a few of its Requirement's own words in parentheses, the naming rule 2 gives every row below `direct` — `failed: R1 (UK work eligibility without sponsorship)`, `unconfirmed: R8 (Permanent contract, not fixed-term)`. The conflict itself — what the candidate has against the gate — is not in the parentheses; it is rule 6's, in what would change this. Then the met ones, which are the `direct` rows, with their fit — ``met: R9 `direct` ``. Those three are every fit a gate row can take (`references/evidence-model.md`, "A gate is met, not established, or failed"), so the line never has an `adjacent` or `absent` gate row to file: a map that holds one is wrong, and filing it as met would hide the error. When none failed the line opens `none failed`, and the met rows sit in its parentheses: ``none failed (R1 `direct`, R9 `direct`); unconfirmed: R8 (Permanent contract, not fixed-term)``. Where the candidate's constraints were not given (`candidate_constraints.status` is `unknown`), the line ends `; candidate constraints not given — checks against them unknown`: that is the flag `SKILL.md`'s input contract puts in the snapshot, and without it a line built from the JD's gates alone reads as an all-clear on checks nobody ran. With no gate rows: `none stated`, plus that clause when it applies. "none failed" is a set claim like any other in the snapshot, and lawful as any is (`references/evidence-model.md`, "The row is the unit"): its parentheses name every row it covers, and it is true of each. `references/dossier-worked-report.md` shows the worked line and the same map with a failed gate.
5. Severe red flags: every `severity: high` register entry by ID, written with its full token — "RR5 (`severity: high`)" — or "none found". A bare `high`, `medium`, `low` or `none` in the snapshot is always a confidence band and sits only beside the one map row it belongs to; the two vocabularies share their words, and a severity written like a band is read as one.
6. What would change this: for `conditional_go` the conditions; for `hold_pending_answers` the awaited answers; for `no_go` the facts that would have to be different.

**Two slots, not one paragraph, and each one reads a named table.** The rule that
both ledgers appear was already here and was already true, and the snapshot was
still the place world-claims collected: a comparison with the typical candidate
for the title, a verdict that the mandate was genuine and well scoped, a claim
that companies of that size routinely have thin public footprints —
every one of those graded as an unlabeled assertion about the world, and every one
was written into a slot that said "two or three sentences" and named no referent.
A slot bound to a table has a test the writer can apply while writing: **which row
is this sentence reading?** A clause with no answer is not a rationale, it is a
new claim, and a new claim belongs in a row where it gets a Provenance cell — or
nowhere. The snapshot asserts nothing the tables beneath it do not already carry;
it is the reading, and the reading is the one thing here that needs no label.

**Every number the response states about itself is checked against itself — and the fit ledger states none.** It is a projection, so there is nothing in it to recount: no total, no fraction, no quantifier from the lists in `references/evidence-model.md` ("The row is the unit"), named or not, and no band summarised over rows. A confidence band appears in the snapshot only beside the one row it belongs to — R4 (`medium`) — because "`high` confidence" over a map whose rows are all `medium` is the same error as a wrong count. The ledger was a count for as long as this skill has existed, and the worked example taught it with a wrong one from v0.1: "five of seven material requirements are `direct`" above a map with four, its eligibility gate counted once by ID and again by name. Measured runs copied the form and got it wrong the same way — counting R-numbers while listing rows, or reading "must-have" from the JD's list while the map had tiered a responsibility `must_have` — and every per-row reading in those snapshots was right. A number about map rows anywhere else is held to the rule in `references/evidence-model.md` ("The row is the unit"). Every other number the prose makes about its own contents — "three things to firm up" above a list of two, "two open questions" in a summary and three in the queue — is named rather than counted where it can be, and recounted from what is actually there on the first pass and on every regeneration where a count is kept. A reader who counts differently stops trusting the analysis rather than the sentence, and they are right to, because the tally was the cheapest thing in the document to get right.

Regenerate the snapshot on every turn that changes the map or the register — a stale decision over fresh evidence is the inconsistency readers notice first.
