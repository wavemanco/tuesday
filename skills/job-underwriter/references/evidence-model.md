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

| Need | Section of the mirror |
|---|---|
| Which `source_type` a piece of evidence carries | §1 |
| Which `confidence` band a candidate claim earns | §2 |
| Whether a written line is `[grounded]`, `[inferred]`, or `[generic]` | §4 |
| What may be asserted on top of a claim at each band | §5, including the two overrides that beat every label |
| The never-do list binding every output | §6 |

Three readings this skill adds on top, because they concern its own intake and
output rather than the shared vocabulary:

- **Prose background is CV-equivalent at intake.** A candidate background typed
  into the conversation is self-report of the same standing as `cv` — leads for
  verification, not proof. Once the candidate answers a specific probe about it,
  that answer is `user_confirmed_text`.
- **`medium` is the intake ceiling.** Nothing reaches `high` on a first pass from
  unprobed material, however specific it sounds: `high` needs an inspectable
  artifact, and intake prose is not one.
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
- **Every enum cell holds exactly one token from its set, and nothing else.** `priority`, `fit_status`, `confidence`, `gap_type`, and the register's `class` and `severity` are vocabularies, not prose: no slash, no hyphenated pair, no parenthetical, no second answer. `low–medium`, `none/low`, `split`, `mixed` and `discovery (sales piece)` have each been written into one of these cells, and the list keeps growing because each is a different way of declining to choose — two answers, or a qualifier smuggled into a slot with room for one. The qualifier is not unwelcome; it belongs in `reasoning`, where it can be read and where nothing downstream tries to parse it. Hedging between two declines to make the call the row exists to make. The mapping governs what may be asserted on top of each band, so a hybrid licenses nothing coherently. When a claim genuinely sits between two, take the **lower** band and say why in `reasoning`: the lower band is the one whose assertions the evidence can actually carry, and the reasoning is where the nuance belongs. When one requirement holds two claims of different strength, the split is legitimate and the slash is not: it becomes **two rows** — R4a at `medium` for the adjacent work, R4b at `none` for the titled years — each with its own requirement text, band and next action. Written into one cell as "medium (adjacent) / none (titled)" it is still one cell holding two answers, and everything downstream that reads a band off this row now reads a string. Rows are free; the cell is the constraint.
- **A cell restates the source claim; it never widens it.** The map is the spine — the plan, the handoff, and every draft line read from these rows, so a qualifier dropped here ("on custom builds" quietly becoming "across 30+ integrations") propagates into language the candidate says out loud. Carry the user's own qualifiers into the cell, and when a cell needs a broader claim to be true, that is a `next_action`, not a wording choice.
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
