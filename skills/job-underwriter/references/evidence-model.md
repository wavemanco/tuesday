# Evidence model

The evidence map is the skill's spine: one row per material JD requirement, tracing claim → evidence → confidence, so that every downstream artifact — the gap queue, the application plan, the decision, the handoff — reads from rows rather than from impressions.

The vocabulary it uses is defined in `references/evidence-conventions.md`, the suite's canonical file mirrored verbatim into this skill; what follows is the row shape this skill fills in with it.

## The vocabulary

Source types, confidence bands, provenance labels, and the mapping that connects
them are defined in `references/evidence-conventions.md` — the suite's canonical
vocabulary, mirrored verbatim into this skill. Read the definitions there rather
than from memory: the whole suite speaks one dialect, and a skill that quietly
redefines a band or coins a synonym breaks every consumer downstream of it.

What that file settles, and where:

| Need | Where it is settled |
|---|---|
| Which `source_type` a piece of evidence carries | `evidence-conventions.md` §1 |
| Which `confidence` band a candidate claim earns | `evidence-conventions.md` §2 |
| Whether a written line is `[grounded]`, `[inferred]`, or `[generic]` | `evidence-conventions.md` §4 |
| What may be asserted on top of a claim at each band | `evidence-conventions.md` §5, including the overrides that beat every label |
| The never-do list binding every output | `evidence-conventions.md` §6 |

Three readings this skill adds on top, because they concern its own intake and
output rather than the shared vocabulary:

- **Prose background is CV-equivalent at intake.** A candidate background typed
  into the conversation is self-report of the same standing as `cv` — leads for
  verification, not proof. Once the candidate answers a specific probe about it,
  that answer is `user_confirmed_text`.
- **`medium` is the intake ceiling.** Nothing reaches `high` on a first pass from
  unprobed material, however specific it sounds: `high` needs an inspectable
  artifact, and intake prose is not one. The candidate's own stated constraint is
  the exception `evidence-conventions.md` §2 names, and the constraint-row rule
  below applies it.
- **A provenance label attaches to the sentence it licenses, not to the section.**
  A heading that announces research, or a preamble saying what follows is
  inferred, leaves every line beneath it bare the moment one is quoted back,
  pasted into the dossier, or read on its own — and an unlabeled inference reads
  exactly like a fact. Label at the point of assertion and accept the repetition;
  the labels are not decoration on the analysis, they are how a reader tells
  which parts of it can be checked. They are also not a research-only device:
  a reading drawn from the JD and the CV alone is `[inferred]`, and a claim
  about what roles of this kind are normally like is `[generic]`, whether or
  not any search ran. A run with no research is *more* inference, not less, so
  a response that labels nothing because it searched nothing has it backwards.
  A label marks where a statement about *the world* came from — the employer,
  the market, the role, the candidate's experience. The skill's reasoning about
  its own analysis is not a claim about the world and carries no label: "this is
  a fit case with a title problem, not a substance problem" is a reading of the
  map the reader can already see. The distinction is not a loophole, and the way
  it gets abused is worth naming — "an interviewer will probe this hardest" and
  "a keyword screen never lets a human read that far" look like commentary and
  are claims about how hiring works, which is the world. If a sentence would
  still assert something were the analysis deleted, it is a world-claim and it
  carries its label.

  And a derived claim lives in a row, not in prose. Every structure that carries
  derived judgment has a provenance column — the role-reality table, the evidence
  map's `reasoning`, the register's hypothesis — so free prose in the assessment
  carries only what could be quoted from the JD, the CV, or the user's own words.
  The moment a sentence adds a reading of its own, it belongs in the row it is a
  reading of, and a reading with no row to sit in is a reading to cut. This is
  the fourth attempt at this rule and the first that is not a reminder: three
  wordings asked the writer to remember a label, and a writer who knows where a
  claim came from cannot see the sentence that fails to say so. An empty cell is
  visible; a missing suffix is not.

  It is canonical now — `references/output-discipline.md` rule 6 — and it has two
  mechanisms behind it rather than a fifth wording. `provenance_sections` declares
  which sections carry the column and CI checks each one really does. And the
  decision snapshot, which is where world-claims collected because it was the last
  free paragraph in the assessment, no longer has one: its rationale is two slots,
  a fit ledger reading the evidence map and an opportunity ledger reading the
  register, each naming the row IDs it reads. The test a writer can apply while
  writing is *which row is this sentence reading?* — and a clause with no answer is
  a new claim, which belongs in a row or nowhere.

## The evidence-map row

One row per material requirement. A requirement is material when it plausibly affects the decision or the application strategy: every hard gate and must-have, important requirements, and any preferred requirement the candidate could meaningfully differentiate on. Boilerplate ("self-starter") is not material unless the risk register says otherwise.

```yaml
requirement_id: R1                     # stable within the engagement; the gap queue and plan refer to it
requirement: "..."
priority: hard_gate | must_have | important | preferred
requirement_source:
  type: jd_quote | inferred
  text: "..."                          # the exact JD language, or the named basis for the inference
fit_status: direct | adjacent | unclear | absent | hard_gate_fail   # a hard_gate row: direct, unclear or hard_gate_fail only (rules below)
candidate_claim: "..." | null          # null when no claim exists yet
evidence:
  - source_type: cv | prior_resume | attachment | link | user_confirmed_text | user_confirmed_voice | memory_lead | inference
    reference: "..."                   # which document, which answer, which URL
    quote_or_summary: "..."
verified: true | false                 # true only when user-confirmed AND specific
confidence: high | medium | low | none
gap_type: none | presentation | discovery | transferability | capability | hard_gate
reasoning: "..."                       # why this status and confidence; name any derivation
provenance: "[grounded] | [inferred] | [generic], with the basis named"
next_action: "..."                     # always concrete: the question to ask, the artifact to request, the edit to propose, or "none"
```

Rules for building rows:

- **Requirements come from the JD or from named inference, never from buzzword drift.** "Mentions a mapping tool once in a tools list" does not create a GIS-analysis requirement; if you infer a requirement, `requirement_source.type: inferred` and say why.
- **`fit_status` and `gap_type` are decided per the taxonomy** in `references/gap-taxonomy-and-questions.md`, and they are two calls, not one. When fit is `direct` with solid evidence the CV already communicates, `gap_type: none`; when fit is `direct` but the CV buries the evidence, the gap is `presentation`. Every row carries a gap type, `none` included — it is a token in the vocabulary (`references/evidence-conventions.md` §3), not an empty cell.
- **Every enum cell holds exactly one token from its set, and nothing else.** `priority`, `fit_status`, `confidence`, `gap_type`, and the register's `class` and `severity` are vocabularies, not prose: no slash, no hyphenated pair, no parenthetical, no second answer. `low–medium`, `none/low`, `split`, `mixed` and `discovery (sales piece)` have each been written into one of these cells, and the list keeps growing because each is a different way of declining to choose — two answers, or a qualifier smuggled into a slot with room for one. The qualifier is not unwelcome; it belongs in `reasoning`, where it can be read and where nothing downstream tries to parse it — **and `reasoning` is a rendered column of the evidence map, not a field that only surfaces in the JSON.** The column was missing for longer than anyone noticed, which is why the list of coined values above kept growing: the rule named a destination the writer could not see. If you are about to write a map without that column, add the column first. Hedging between two declines to make the call the row exists to make. The mapping governs what may be asserted on top of each band, so a hybrid licenses nothing coherently. When a claim genuinely sits between two, take the **lower** band and say why in `reasoning`: the lower band is the one whose assertions the evidence can actually carry, and the reasoning is where the nuance belongs. When one requirement holds two claims of different strength, the split is legitimate and the slash is not: it becomes **two rows** — R4a at `medium` for the adjacent work, R4b at `none` for the titled years — each with its own requirement text, band and next action. Written into one cell as "medium (adjacent) / none (titled)" it is still one cell holding two answers, and everything downstream that reads a band off this row now reads a string. Rows are free; the cell is the constraint.
- **Every hard constraint the role's terms touch is carried by one `hard_gate` row — one row per gate term, whichever side states it.** Each `kind: hard` entry in `candidate_constraints` the role's terms bear on, stated or silent, is carried by a row. Where the JD already has a hard-gate row for the same term — location, schedule, pay, authorization, travel — that row carries the constraint: its `requirement_source` stays `jd_quote`, the candidate's non-negotiable is its `candidate_claim`, its evidence cites the candidate's statement, and no second row is made; R1 in `references/dossier-template.md` and the `hard_gate_fail` example below are this form. Where the JD has no hard-gate row for the term — the posting is silent on it, or mentions it only in passing — the constraint becomes its own row, `requirement_source.type: inferred` with the text `candidate_constraints: …`, as R8 and R9 in the worked dossier show. Either way the row's fit is `hard_gate_fail` where the terms conflict, `unclear` where they are unstated, `direct` where they are met, as the next rule requires of every gate row; its gap type is `hard_gate` on a failed or unclear row and `none` on a met one (`evidence-conventions.md` §3); and the constraint item's `satisfied_by_role` agrees (no, unknown, yes). On such a row `candidate_claim`, `evidence`, `verified` and `confidence` grade the candidate's own statement of the constraint, not whether the role meets it: a specific, user-confirmed constraint is `verified: true` at `high` (`evidence-conventions.md` §2), and an unconfirmed or vague one takes the band its evidence earns. Whether the role meets it lives in `fit_status`, `gap_type`, `satisfied_by_role` and `reasoning`, never in `confidence`. The register's mismatch entries stay, citing the row ("see R8"); they are never the only place a conflict lives, because the snapshot's hard-gates line reads the map, and a conflict filed only in the register is one it cannot see.
- **A gate is met, not established, or failed — nothing between.** A gate is a term, not experience: a `hard_gate` row is a term the candidate meets or does not — authorization, licence, location, schedule, pay, travel, a credential, a legal constraint. A length-of-experience requirement ("3+ years X", even marked "required") is not a gate: it keeps the tier the posting gives it and is read on the fit scale, because work near it is evidence, not a near miss; it is a gate only when the posting ties it to a legal or credential bar, and is then read as that credential. A `hard_gate` row's fit is one of three: `direct` (met), `unclear` (not established: the material or the role's terms do not settle it), or `hard_gate_fail` (failed); and `hard_gate_fail` is a `hard_gate` row's fit only. A gate row is never `adjacent`: work near a gate does not meet it, so a near miss — a licence held in another country, a clearance one level below the one required — is `hard_gate_fail`, with the nearness in `reasoning` and any path to resolution in `next_action`. It is never `absent` either: a gate the candidate confirms they do not meet is `hard_gate_fail`, and one nothing in the material settles stays `unclear` until it is answered, which is the one question `references/gap-taxonomy-and-questions.md` lets a hard gate ask. The snapshot's hard-gates line reads the map on this rule (`references/risk-and-decision.md` rule 4): it files a gate row as failed, unconfirmed or met, and a gate row with any other fit is one it could only misfile as met.
- **The row is the unit, and a statement about a set of rows names them.** Once a JD responsibility becomes a row, or a requirement splits into R4a and R4b, the JD's own list and the map are two different sets, and a count that is right in one is wrong in the other. Measured snapshots went wrong in exactly that gap: "six of nine" counted R-numbers while its parenthesis listed rows, and "every must-have" read the JD's list while the map had tiered a responsibility `must_have`. So anything the response says about the map, anywhere in it, reads the map's rows and its Priority column — "must-have" means the `must_have` tier — names the IDs it covers, and carries no count, fraction or quantifier over the map or a tier of it: no "N of M", "every", "all", "each of", "only", "the one", "none of", "both", "neither", "the rest", "no other", "any other", or "no `must_have` row" — and in the one sentence after the snapshot's fit ledger, which is about the map by construction, no bare "none" either, because it speaks for the rows that sentence does not name. Plain "no" and the token `none` in backticks, a band or a gap type, are not quantifiers. One form is allowed, because it lists every row it covers: the snapshot's hard-gates line, "none failed (R1 `direct`, R9 `direct`)" (`references/risk-and-decision.md`). Naming loses nothing a count carried, and a list of IDs is the one form a reader can check against the table. This governs how the map is read, not how it is tiered; which tier a responsibility gets is still the row's own call.
- **A cell restates the source claim; it never widens it.** The map is the spine — the plan, the handoff, and every draft line read from these rows, so a qualifier dropped here ("for the arts fund" quietly becoming "across all four funds") propagates into language the candidate says out loud. Carry the user's own qualifiers into the cell, and when a cell needs a broader claim to be true, that is a `next_action`, not a wording choice.
- **Contradictions lower confidence to `none` and say so in `reasoning`** — a CV claiming 5 years against a portfolio showing 2 is a contradiction to surface, not average.
- **`reasoning` carries a world-claim, so it carries a `provenance` label.** This
  column was added to give a hedged confidence value somewhere to go, and it
  immediately became the largest unlabeled assertion surface in the response —
  six graders out of ten pointed at it in one run-set: "the Reasoning column
  asserts numerous facts", "R4b's cell asserts an unlabeled generic-pattern
  claim". The lesson is the one this file already teaches, learned again at cost:
  a new free-text column is a new place for world-claims, and it needs its label
  beside it from the first version rather than the second. Where a cell only
  reads the row — "confirmed and specific, but no inspectable artifact yet" —
  `[grounded]` names the evidence it read. Where it reaches past the row —
  "funders of this size usually split assessment from grant management" — that clause is `[generic]`, and
  the pull to write `[inferred]` is the thing to resist; a cell that does both
  carries both labels, each beside its clause, as `evidence-conventions.md` §5
  allows.
- **`next_action` is where recovery starts.** A row with an unresolved gap and no concrete next action is an unfinished row.

## The confirmation card

When the user answers a gap question — text, transcript, attachment, or link — extract before you upgrade. Present back, compactly:

```text
What I heard: [claim, in one sentence]
Ownership: [what was theirs vs. the team's]
Scope: [team / users / revenue / stakes — whatever was stated]
When: [period, if stated]
Outcome: [result or metric, if stated]
Artifact: [anything inspectable that was offered]
Missing for full strength: [the one or two specifics that would raise confidence]

Right, or should I correct something?
```

Only after the user confirms (or corrects) does the row update: source becomes `user_confirmed_text` / `user_confirmed_voice`, confidence per the bands, dependent recommendations regenerated. A rejected extraction is recorded in `evidence_state.rejected_inferences` so it is never re-derived.

## Worked micro-examples

A `direct` row at `high` confidence — claim, artifact, done:

```yaml
requirement_id: R2
requirement: "Assessing applications against published criteria"
priority: must_have
requirement_source: { type: jd_quote, text: "experience assessing applications against published criteria" }
fit_status: direct
candidate_claim: "Lead assessor for a community fund's two annual rounds, 2022-2026"
evidence:
  - source_type: cv
    reference: "CV, Experience"
    quote_or_summary: "Assessor, then lead assessor, community fund, 2022-2026"
  - source_type: link
    reference: "the fund's published panel report (fetched)"
    quote_or_summary: "Names her as lead assessor for both rounds; prints the criteria and the scoring bands used"
verified: true
confidence: high
gap_type: none
reasoning: "Specific, confirmed, and inspectable — CV claim plus a read artifact."
next_action: "none"
```

A `discovery` row born from a `memory_lead` — the lead prompts a question, nothing more:

```yaml
requirement_id: R5
requirement: "Has written guidance applicants rely on"
priority: important
requirement_source: { type: jd_quote, text: "you will rewrite how first-time groups apply to us" }
fit_status: unclear
candidate_claim: null
evidence:
  - source_type: memory_lead
    reference: "prior conversation"
    quote_or_summary: "May have redrafted a fund's eligibility notes for first-time applicants — unconfirmed"
verified: false
confidence: low
gap_type: discovery
reasoning: "A lead exists but nothing is confirmed; the CV is silent. Low, not none, because there is a concrete thread to pull."
next_action: "Ask: what did the redraft change, which part was theirs, did applicants use it, and is there a copy to look at?"
```

A `hard_gate_fail` row — plain, prominent, unsolvable by wording. It is also the merged form of the constraint-row rule above: the JD's own gate row carries the candidate's non-negotiable, and no second row is made for it:

```yaml
requirement_id: R8
requirement: "Two nights a month away on project visits"
priority: hard_gate
requirement_source: { type: jd_quote, text: "visits to funded projects mean two nights away each month; this is essential" }
fit_status: hard_gate_fail
candidate_claim: "No overnight stays away from home, stated as a non-negotiable"
evidence:
  - source_type: user_confirmed_text
    reference: "intake message"
    quote_or_summary: "Day trips are fine, but I can't stay away overnight"
verified: true
confidence: high
gap_type: hard_gate
reasoning: "Confidence grades her statement of the limit, which is her own, specific and confirmed. The fit is a failed gate because the JD calls the overnight visits essential and her limit rules them out."
next_action: "Surface in the decision snapshot; only the user or the employer changing terms resolves it."
```

## Serialization

Rows serialize into the dossier envelope's `evidence_map` section unchanged — same field names, JSON instead of YAML. The full envelope, with every section in place, is in `references/dossier-template.md`.
