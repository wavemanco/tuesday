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

**What counts as an inspectable artifact is domain-specific, and it is researched
rather than assumed.** The `high` band turns on "an inspectable artifact", and one
does not look the same in two fields: a repository in engineering, a portfolio in
design, a deal sheet in sales, a P&L in management, a publication list in
research, a licence number in a regulated trade, a case outcome in law. A skill
that asks a designer for a repository is asking for the wrong proof, and it will
record `medium` where `high` was available — not because the evidence was weak
but because nobody named the artifact that would have shown it.

The split is the same one `output-discipline.md` draws. The **invariant** is that
a band is set by what can be inspected and never by how impressive the claim
sounds, and that wherever a band could be raised, the upgrade menu names the
specific artifact that would raise it. What **varies** is the artifact vocabulary
for this role's domain, and that is a research question — bounded, with a
checkable answer — governed by `interaction-grammar.md` §4.

This one does not become a declared parameter. The output-discipline parameters
are a skill's standing design decisions and CI checks them; this one is different
in kind, because it changes with the role in front of the skill rather than with
the skill. A static declaration would be wrong on the second engagement.

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
- **`[generic]` may not support an entity-specific assertion.** This one is a restatement of §4 rather than a new constraint: `[generic]` is *defined* as a role-family pattern carrying no entity-specific claim, so it cannot be the evidence for one. A pattern may describe, illustrate, calibrate, or furnish rehearsal material. It may not be the support for a statement about **this** candidate or **this** employer.

  The distinction that keeps this from eating the degradation ladder: a `[generic]` question bank asserts that roles of this kind get asked things of this kind, which is true, honestly labeled, and exactly what the label means. A `must_have` evidence-map row at `[generic]` asserts that *this person* does or does not meet *this requirement* on the basis of a pattern — an entity-specific claim resting on material that by definition contains none. The first is the suite working as designed. The second is a conclusion with nothing under it.

  So the rule has a cell rather than a judgment: **a row whose subject is the candidate or the employer may not carry `[generic]` as its provenance.** In job-underwriter that is every evidence-map row and every register entry a decision status reads; in resume-tailor, a proposed line's trace. Where one has only `[generic]` under it, either a `[grounded]` source is found, or the claim is withdrawn and the gap named — and naming the gap is the honest output, not the failure.

Why the third override exists, and why it is newer than the other two:

Cui, Dias & Ye (2025) measured what happens to a signal once generative AI makes
it cheap to produce. On a large freelancing platform, the correlation between how
closely a cover letter matched its job post and whether it drew a callback **fell
51%**, and for offers **79%**, while the weight employers put on records that
cannot be written on demand rose. The generalisation is not about cover letters:
**whatever becomes cheap to generate stops carrying information, and what remains
is what can be checked.**

`[generic]` is this suite's own name for the cheap-to-generate part. An output
whose load-bearing claims rest on it is built from exactly the material that
deflates. Keeping `[generic]` non-load-bearing is therefore not a purity rule —
it is the part of the work that stays worth something.

Two honesty notes, because this override rests on external evidence rather than
on a defect this repository measured. The study is one platform, remote freelance
work, where a platform-native review score exists and dominates default ranking;
generalising it to hiring at large is an **inference**, and it is recorded as one.
And the authors flag a consequence this suite inherits by adopting the rule: a
shift toward harder-to-fake history favours established candidates over newcomers.
A suite that leans on verifiable proof is, without intending it, hardest on
career-changers and early-career people — who are a large share of who needs it.
The answer is not to relax the rule, which would only sell them a signal that has
already deflated. It is that `not_evidenced` and `capability` must stay
first-class, actionable outputs with real closure paths, rather than polite
endings.

## 6. Truthfulness core

Shared never-do list, binding on every skill:

- Never add an unverified claim to a CV, cover letter, outreach note, work sample, or rehearsed answer.
- Never convert a `memory_lead` into asserted experience.
- Never inflate a prototype into production experience, or participation into leadership.
- Never invent metrics, team sizes, customer counts, revenue, dates, credentials, or titles.
- Never reduce fit to a single opaque numerical score.
- Never fabricate facts about a company, interviewer, or process; when uncertain, drop the fact rather than hedge it.
- Coaching rehearses precise honesty — "what was actually you" — never spin. Questions that probe attribution exist because interviewers ask them; the preparation is candor, rehearsed.
