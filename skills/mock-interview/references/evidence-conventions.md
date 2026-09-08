<!-- SYNCED FROM: conventions/evidence-conventions.md
     Canonical wins on conflict. Everything below this comment block is a
     verbatim copy of the canonical file — do not edit it here. Fixes flow
     canonical -> mirror, never the reverse; a mirror that drifts is a defect.
     A byte check strips this header and compares the remainder to canonical. -->
# Evidence conventions

Canonical for every skill in Tuesday, and for any later surface (agent, MCP, UI renderer) that consumes their outputs. Skills carry a mirror of this file in their `references/` with a synced-from header; this copy wins on conflict.

The system's one promise underneath all of it: **nothing a skill writes may outrun the evidence it stands on, and the reader can always see how far the evidence goes.**

## 1. Evidence source types

Every piece of candidate evidence records where it came from. One vocabulary, all skills:

| Source type | Meaning | Reliability note |
|---|---|---|
| `jd_quote` | Exact language from the job description | Authoritative for what the employer *says*; not for what the role *is* |
| `cv` | The candidate's current resume | Self-reported; claims here are leads for verification, not proof |
| `prior_resume` | An earlier resume version | Often contains evidence the current CV dropped |
| `attachment` | Uploaded document: review, brief, deck, certificate, work sample | Strong when inspectable; record what was actually inspected |
| `link` | Portfolio, repository, published work | Strong when fetched and read; a URL alone proves nothing |
| `user_confirmed_text` | The candidate answered a question in writing | Confirmed claim; strength depends on specificity |
| `user_confirmed_voice` | The candidate answered by voice / pasted transcript | Same standing as confirmed text once extracted facts are user-approved |
| `memory_lead` | Agent memory suggests relevant experience | **Unverified until the user confirms and specifies it.** Never cite as evidence; only as the basis for a question |
| `web_research` | Fetched public material (official page, guide, forum) | Official > company careers material > reputable guides > forums; forum-only claims never rise above inferred |
| `inference` | A skill's own derivation | Must name what it derives from; the weakest source by definition |

## 2. Evidence confidence bands

Confidence grades a **candidate claim**, not a skill's prose:

| Confidence | Meaning |
|---|---|
| `high` | Specific, user-confirmed claim supported by an inspectable artifact — CV plus a document, link, or direct evidence |
| `medium` | User-confirmed, specific, plausible — but limited inspectable proof |
| `low` | Vague claim, indirect context, partial evidence, or an unconfirmed `memory_lead` |
| `none` | No supporting evidence, or direct contradiction |

## 3. Fit status and the gap taxonomy

Per material requirement, fit status is one of: `direct`, `adjacent`, `unclear`, `absent`, `hard_gate_fail`. **Every material requirement also carries a gap type** — `none` where nothing needs recovering, one of the five others where something does. Fit status does not decide it: a `direct` row whose evidence the CV buries is a `presentation` gap, so the gap type is a separate call on a separate axis.

| Gap type | Definition | Appropriate next action |
|---|---|---|
| `none` | Nothing to recover: the evidence exists and the CV already communicates it in role-relevant terms | None; the row is closed |
| `presentation` | Verified evidence exists; the CV doesn't communicate it in role-relevant terms | Propose a truthful repositioning, contingent on user approval |
| `discovery` | Evidence may exist; current inputs are inconclusive | Ask one targeted, example-rich question; suggest exact artifacts |
| `transferability` | No direct match, but credible adjacent work | Make the transferable case *and its limits*; consider a work sample |
| `capability` | No credible direct or adjacent evidence | Name a realistic closure path, or carry as material risk |
| `hard_gate` | Eligibility, credential, or constraint not met | Surface prominently; wording cannot solve it and no skill may imply otherwise |

The taxonomy exists because "missing from the CV" is four different situations wearing one costume, and only one of them is a real capability problem.

`none` is a token and not an empty cell. This is the sixth member because the five were written as the answers to "what kind of gap is this?" and the settled row was left with no answer at all — so an enum column arrived with nothing to put in it, and the value got invented at write time. `none` was already being emitted: `evidence-model.md`'s row spec has declared it since job-underwriter v0.1, the worked dossier writes it, and the JSON envelope carries it. What was missing was this line, and a vocabulary that a skill has quietly extended is the drift this file exists to prevent — whichever side turns out to be right.

## 4. Content provenance labels

Provenance labels grade **what a skill wrote** — a question, a fit row, a research claim, a coaching line:

| Label | Meaning |
|---|---|
| `[grounded]` | Traceable to a provided document, a user-confirmed claim, or research cited in Sources |
| `[inferred]` | Derived from a representative or adjacent source — a researched typical JD, a reasonable extension of a grounded fact. The derivation is named |
| `[generic]` | Role-family pattern with no entity-specific claim. Useful rehearsal, no factual assertion |

## 5. The mapping — how confidence and provenance connect

The two axes measure different things: confidence grades the candidate's evidence; provenance grades the skill's output. They meet whenever a skill writes something *on top of* candidate evidence:

| Evidence confidence | What a skill may write from it | Provenance of that output |
|---|---|---|
| `high` | Assert it as the candidate's story; build guidance, bullets, and answers on it | `[grounded]` |
| `medium` | Assert it **with the verification caveat named** ("confirmed, limited inspectable proof — expect a probe") | `[grounded]`, caveat visible |
| `low` | Never assert as the candidate's claim. May appear only as a discovery lead, a question, or a clarify-strategy coaching note | `[inferred]`, derivation named |
| `none` | May not appear as candidate capability at all — only as a named gap or hard-gate surfacing | — |

Two overrides that beat every label:

- **`prohibited_claims` are absolute.** If the dossier lists a claim as prohibited, no skill output may assert it, soften it, or coach an answer that implies it — whatever any label says.
- **Hard-gate failures stay visible.** No aggregate framing, positive tone, or fit elsewhere may bury a `hard_gate` finding.

## 6. Truthfulness core

Shared never-do list, binding on every skill:

- Never add an unverified claim to a CV, cover letter, outreach note, work sample, or rehearsed answer.
- Never convert a `memory_lead` into asserted experience.
- Never inflate a prototype into production experience, or participation into leadership.
- Never invent metrics, team sizes, customer counts, revenue, dates, credentials, or titles.
- Never reduce fit to a single opaque numerical score.
- Never fabricate facts about a company, interviewer, or process; when uncertain, drop the fact rather than hedge it.
- Coaching rehearses precise honesty — "what was actually you" — never spin. Questions that probe attribution exist because interviewers ask them; the preparation is candor, rehearsed.
