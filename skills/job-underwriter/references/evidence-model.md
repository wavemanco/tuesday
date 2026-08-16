# Evidence model

The evidence map is the skill's spine: one row per material JD requirement, tracing claim → evidence → confidence, so that every downstream artifact — the gap queue, the application plan, the decision, the handoff — reads from rows rather than from impressions. This file defines the vocabulary and the row shape.

Vocabulary here is an operative copy of `conventions/evidence-conventions.md` (canonical — it wins on any conflict). Do not coin synonyms; the suite has one dialect.

## Evidence source types

Every piece of candidate evidence records where it came from:

| Source type | Meaning | Reliability note |
|---|---|---|
| `jd_quote` | Exact language from the job description | Authoritative for what the employer *says*; not for what the role *is* |
| `cv` | The candidate's current resume | Self-reported; claims here are leads for verification, not proof |
| `prior_resume` | An earlier resume version | Often contains evidence the current CV dropped |
| `attachment` | Uploaded document: review, brief, deck, certificate, work sample | Strong when inspectable; record what was actually inspected |
| `link` | Portfolio, repository, published work | Strong when fetched and read; a URL alone proves nothing |
| `user_confirmed_text` | The candidate answered a question in writing | Confirmed claim; strength depends on specificity |
| `user_confirmed_voice` | The candidate answered by voice / pasted transcript | Same standing as confirmed text once extracted facts are user-approved |
| `memory_lead` | Agent memory or prior context suggests relevant experience | **Unverified until the user confirms and specifies it.** Never cite as evidence; only as the basis for a question |
| `web_research` | Fetched public material (official page, guide, forum) | Official material first; forum-only claims never rise above inferred |
| `inference` | This skill's own derivation | Must name what it derives from; the weakest source by definition |

A candidate background stated in prose in the conversation is `cv`-equivalent self-report at intake; once the candidate answers a specific probe about it, the answer is `user_confirmed_text`.

## Evidence confidence bands

Confidence grades a **candidate claim**, not this skill's prose:

| Confidence | Meaning |
|---|---|
| `high` | Specific, user-confirmed claim supported by an inspectable artifact — CV plus a document, link, or direct evidence |
| `medium` | User-confirmed, specific, plausible — but limited inspectable proof |
| `low` | Vague claim, indirect context, partial evidence, or an unconfirmed `memory_lead` |
| `none` | No supporting evidence, or direct contradiction |

## Content provenance labels

Provenance grades **what this skill wrote** — a fit row's reasoning, a research claim, an inferred outcome:

- `[grounded]` — traceable to a provided document, a user-confirmed claim, or research cited in the sources.
- `[inferred]` — derived from a representative or adjacent source, with the derivation named.
- `[generic]` — role-family pattern with no entity-specific claim.

## The mapping — what may be written on top of evidence

| Evidence confidence | What this skill may write from it | Provenance of that output |
|---|---|---|
| `high` | Assert it as the candidate's story; build plan items and draft bullets on it | `[grounded]` |
| `medium` | Assert it **with the verification caveat named** ("confirmed, limited inspectable proof — expect a probe") | `[grounded]`, caveat visible |
| `low` | Never assert as the candidate's claim. May appear only as a discovery lead or a question | `[inferred]`, derivation named |
| `none` | May not appear as candidate capability at all — only as a named gap or hard-gate surfacing | — |

Two overrides beat every label: **`prohibited_claims` are absolute**, and **hard-gate failures stay visible** — no mapping row, tone, or aggregate framing may bury either.

## The evidence-map row

One row per material requirement. A requirement is material when it plausibly affects the decision or the application strategy: every hard gate and must-have, important requirements, and any preferred requirement the candidate could meaningfully differentiate on. Boilerplate ("self-starter") is not material unless the risk register says otherwise.

```yaml
requirement_id: R1                     # stable within the engagement; the gap queue and plan refer to it
requirement: "..."
priority: hard_gate | must_have | important | preferred
requirement_source:
  type: jd_quote | inferred
  text: "..."                          # the exact JD language, or the named basis for the inference
fit_status: direct | adjacent | unclear | absent | hard_gate_fail
candidate_claim: "..." | null          # null when no claim exists yet
evidence:
  - source_type: cv | prior_resume | attachment | link | user_confirmed_text | user_confirmed_voice | memory_lead | inference
    reference: "..."                   # which document, which answer, which URL
    quote_or_summary: "..."
verified: true | false                 # true only when user-confirmed AND specific
confidence: high | medium | low | none
gap_type: none | presentation | discovery | transferability | capability | hard_gate
reasoning: "..."                       # why this status and confidence; name any derivation
next_action: "..."                     # always concrete: the question to ask, the artifact to request, the edit to propose, or "none"
```

Rules for building rows:

- **Requirements come from the JD or from named inference, never from buzzword drift.** "Mentions Kafka once in a tools list" does not create a streaming-architecture requirement; if you infer a requirement, `requirement_source.type: inferred` and say why.
- **`fit_status` and `gap_type` are decided per the taxonomy** in `references/gap-taxonomy-and-questions.md`. When fit is `direct` with solid evidence, `gap_type: none`.
- **Contradictions lower confidence to `none` and say so in `reasoning`** — a CV claiming 5 years against a portfolio showing 2 is a contradiction to surface, not average.
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
requirement: "Expert SQL for product analytics"
priority: must_have
requirement_source: { type: jd_quote, text: "expert SQL" }
fit_status: direct
candidate_claim: "Daily SQL on a warehouse for 6 years; wrote the team's query style guide"
evidence:
  - source_type: cv
    reference: "CV, Experience"
    quote_or_summary: "SQL daily on Snowflake; 40+ governed dashboards"
  - source_type: link
    reference: "github.com/example/queries (fetched)"
    quote_or_summary: "Repository of analysis queries; non-trivial window functions throughout"
verified: true
confidence: high
gap_type: none
reasoning: "Specific, confirmed, and inspectable — CV claim plus a read artifact."
next_action: "none"
```

A `discovery` row born from a `memory_lead` — the lead prompts a question, nothing more:

```yaml
requirement_id: R5
requirement: "Has shipped an internal tool to real users"
priority: important
requirement_source: { type: jd_quote, text: "builds tools others rely on" }
fit_status: unclear
candidate_claim: null
evidence:
  - source_type: memory_lead
    reference: "prior conversation"
    quote_or_summary: "May have built a request-triage tool support agents adopted — unconfirmed"
verified: false
confidence: low
gap_type: discovery
reasoning: "A lead exists but nothing is confirmed; the CV is silent. Low, not none, because there is a concrete thread to pull."
next_action: "Ask: what was the tool, what part was theirs, who used it, and is there anything to look at?"
```

A `hard_gate_fail` row — plain, prominent, unsolvable by wording:

```yaml
requirement_id: R8
requirement: "On-site five days a week"
priority: hard_gate
requirement_source: { type: jd_quote, text: "on-site 5 days a week - no exceptions" }
fit_status: hard_gate_fail
candidate_claim: "Remote-only, stated as a non-negotiable"
evidence:
  - source_type: user_confirmed_text
    reference: "intake message"
    quote_or_summary: "I'm remote-only - not relocating"
verified: true
confidence: high
gap_type: hard_gate
reasoning: "The JD's requirement and the candidate's non-negotiable directly conflict. High confidence in the conflict itself."
next_action: "Surface in the decision snapshot; only the user or the employer changing terms resolves it."
```

## Serialization

Rows serialize into the dossier envelope's `evidence_map` section unchanged — same field names, JSON instead of YAML. The full envelope, with every section in place, is in `references/dossier-template.md`.
