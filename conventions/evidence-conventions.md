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

**A candidate's own constraint is the one claim with nothing to inspect.** A
non-negotiable the candidate states about themselves — a pay floor, the office
days they will work, a right to work the suite never asks them to prove — has no
artifact behind it and could not have one: their own specific, confirmed word is
the strongest evidence that exists for it, so it is `high`. The band grades their
statement of the constraint, never whether a role meets it; that is fit, carried
by the fit status and gap type. A vague or unconfirmed constraint takes the band
its evidence earns.

**What counts as an inspectable artifact is domain-specific, and it is researched
rather than assumed.** The `high` band turns on "an inspectable artifact", and one
does not look the same in two fields: a repository in engineering, a portfolio in
design, a deal sheet in sales, a P&L in management, a publication list in
research, a licence number in a regulated trade, a case outcome in law. A skill
that asks a designer for a repository is asking for the wrong proof. `medium` is
the correct band while nothing has been inspected, and stays correct; what breaks
is the upgrade menu, which asks for "supporting material" when it could have
named the one artifact this field actually keeps. The band is not the error. The
vague request that leaves it there is.

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

`none` is a token and not an empty cell. This is the sixth member because the five were written as the answers to "what kind of gap is this?" and the settled row was left with no answer at all — so an enum column arrived with nothing to put in it, and the value got invented at write time. `none` was already being emitted: the underwriter's own row spec has declared it since v0.1, the worked dossier writes it, and the JSON envelope carries it. What was missing was this line, and a vocabulary that a skill has quietly extended is the drift this file exists to prevent — whichever side turns out to be right.

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

Three overrides that beat every label:

- **`prohibited_claims` are absolute.** If the dossier lists a claim as prohibited, no skill output may assert it, soften it, or coach an answer that implies it — whatever any label says.
- **Hard-gate failures stay visible.** No aggregate framing, positive tone, or fit elsewhere may bury a `hard_gate` finding.
- **`[generic]` may not support an entity-specific assertion.** A restatement of §4 rather than a new constraint: `[generic]` is *defined* as a role-family pattern carrying no entity-specific claim, so it cannot be the evidence for one.

  **The test is per clause, not per row.** A cell may hold both, and often should: "`[grounded]` what the resume does and does not say; `[generic]` what this costs on applications of this kind" is two claims wearing two labels, and it is correct. What the rule forbids is a single clause that names *this* candidate or *this* employer and rests on a pattern for its support.

  Three legitimate uses this rule does not touch, named because an earlier draft of it forbade all three:

  - **A register entry whose hypothesis is itself a pattern.** The standing failed-attribution entry ships as `[generic] pattern for companies of this size, not a claim about this one`, and it caps the decision at `conditional_go`. It is read by a decision and it is honest — the label and the sentence agree that no entity claim is being made.
  - **A reasoning cell that reaches past its row.** The skill that owns an evidence map requires `[generic]` exactly there — "funders of this size usually split assessment from grant management" — and names the pull to write `[inferred]` instead as the thing to resist.
  - **An honestly degraded section.** A pack whose research could not run labels its banks `[generic]` and says so. The ladder depends on it, and a smaller honest pack beats a full-looking fabricated one.

  **There is no CI check for this, and the absence is deliberate.** Every mechanical version drafted — no `[generic]` in a row about the candidate, none in the evidence map, none in a table a decision reads — rejects at least one of the three uses above. A check that would reject correct work is worse than no check, and a suite with this many real mechanisms can afford to say where one does not exist. The rule is gradeable instead: an eval can ask whether a named claim about this person or this company rests on nothing but a pattern.

Why the third override exists, and why it is newer than the other two:

It rests on outside evidence rather than on a defect this repository measured,
so its evidence is cited, not paraphrased — see `citations.md`.

On one freelancing platform, once an AI tool made cover-letter tailoring cheap,
"The correlation between cover-letter tailoring and receiving a callback fell by
51% after the launch of the AI tool, and the correlation with receiving an offer
fell by 79%." (cite C1) The authors describe where employers went instead:
"Instead, employers shifted toward other signals less susceptible to AI
influence, such as workers’ past work experience." (cite C21) The shift they
measure is in who gets interviewed; for hiring itself they report "no
corresponding increase in the predictive power of rank percentile for ultimate
hiring decisions" (cite C22).

An earlier version of this paragraph set the 51% fall against a 5% rise in
another correlation and called the gap between them the finding. Those are
relative changes on different bases, not one scale, and the authors
themselves describe the rise in an alternative signal's predictive power as
substantial (cite C22). The shift is theirs to state; the size comparison was
this suite's, and it was wrong.

The reading this suite takes from it is an **inference**, not a result — one
platform, one tool, two skill categories, mostly remote short-term work. Stated as an inference: *whatever
becomes cheap to generate stops carrying information, and what can be checked
keeps carrying it.*
`[generic]` is this suite's own name for the cheap-to-generate part, and an
output whose load-bearing claims rest on it is built from exactly what deflates.
Keeping `[generic]` off entity-specific claims is therefore not a purity rule; it
is the part of the work that stays worth something.

The authors name a consequence, and it stays hedged exactly as they wrote it:
"This shift may have important implications, including favoring established
workers at the expense of newcomers trying to enter the market." (cite C3) Their
*may*, their *workers*, their one platform. Whether anything like it reaches this
suite's users is **unknown** — there is no usage data. The rule is adopted
anyway, because relaxing it would only sell thin-evidence candidates a signal that
has already deflated; `discovery` and `capability` gaps stay first-class outputs
with real closure paths because they are the honest output when evidence is thin,
not because anyone knows who is reading.

## 6. Truthfulness core

Shared never-do list, binding on every skill:

- Never add an unverified claim to a CV, cover letter, outreach note, work sample, or rehearsed answer.
- Never convert a `memory_lead` into asserted experience.
- Never inflate a prototype into production experience, or participation into leadership.
- Never invent metrics, team sizes, customer counts, revenue, dates, credentials, or titles.
- Never reduce fit to a single opaque numerical score.
- Never fabricate facts about a company, interviewer, or process; when uncertain, drop the fact rather than hedge it.
- Coaching rehearses precise honesty — "what was actually you" — never spin. Questions that probe attribution exist because interviewers ask them; the preparation is candor, rehearsed.
