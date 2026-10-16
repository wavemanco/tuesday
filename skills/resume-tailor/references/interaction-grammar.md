<!-- SYNCED FROM: conventions/interaction-grammar.md
     Canonical wins on conflict. Everything below this comment block is a
     verbatim copy of the canonical file — do not edit it here. Fixes flow
     canonical -> mirror, never the reverse; a mirror that drifts is a defect.
     A byte check strips this header and compares the remainder to canonical. -->
# Interaction grammar

How every skill in Tuesday behaves with the user. A person moving between skills should feel the same hands. Canonical here; skills mirror in `references/` with a synced-from header.

## 1. The standalone invariant

Every skill runs to a complete, useful output from raw inputs alone. Artifacts from sibling skills — the dossier, a prior pack, verified evidence — are enhancers by definition, never gates. A skill may say what a missing sibling artifact would add; it may never require one, and never degrade into an advertisement for another skill.

Corollary: skills compose in any order, or not at all. The dossier contract (see `dossier-schema.md`) is read-if-present, append-always-offered, never-required.

## 2. Elicitation policy

- **Analysis leads; questions ride.** Produce the best first-pass output from whatever was provided, in the same response as any questions. A message that is only questions — or only a consent request — costs the user a round-trip for nothing.
- **One clarifying message maximum, at most three questions**, covering only what is missing, structural, and un-researchable. Consent items (deep research, optional modes) ride along; they never drive.
- **Proceed on silence.** If the user ignores or declines, continue down the degradation ladder. Never re-ask.
- **Research before asking.** Never ask the user what the public web knows.
- **Adaptive skills** (those whose product *is* iterative recovery, like the underwriter) may ask again in later turns — but each turn obeys the same shape: updated analysis first, then at most three highest-value questions, ranked by importance × uncertainty × recovery probability × decision impact ÷ user effort.

## 3. Degradation and the upgrade menu

- Degrade by dropping or genericizing sections and labeling provenance — never by inventing specifics. A smaller honest output beats a full-looking fabricated one.
- Every output ends with an **upgrade menu**: each missing input and what adding it concretely unlocks. The menu is how enhancers arrive without gating — make the value visible and let the user pull.
- When a late input arrives, regenerate only the affected sections, lead with a one-line changelog, and check the whole artifact for internal consistency before redelivering.

## 4. Research tiers

- **L0** — provided documents only: chosen by the user, or forced because the host offers no search. Everything else labeled `[generic]`.
- **L1** — default: a small budgeted set of targeted searches (each skill defines its targets and caps). Official sources first; freshness rules per fact class; model memory is never a source for values, processes, or current facts.
- **L2** — deep research: offered exactly once, cost stated, run only on consent; the offer rides an already-needed message or lands in the upgrade menu.
- **Not-attributable rule:** results that can't be attributed to the specific entity (name collisions, no web presence) are treated as not-established — said plainly, archetype fallback named, missing facts listed in the upgrade menu.

**Depth is bounded by what the answer can change.** A search that cannot change
something the skill will actually emit — a row, a band, a gap type, a question
bank, a persona weight, a guidance cell, a recommendation — does not run,
whatever budget is left. This is what the tiers were always implementing, and it
is stated because the tiers describe *how much* and not *what for*: L1's cap is a
ceiling, not a target, and a skill that spends it on questions whose answers
change nothing has followed the letter and missed the point. Name the output a
search could change before running it; if there is none, skip it — **and account
for every declared target where the output already reports its research**: one
row each, starting with the number the skill declares it under, with one label in
its Status cell and the reason beside it. The label follows what happened, facts
first:

- A search was sent for the target: `yes` if any call returned anything, no
  results and nothing attributable included — the row then says "not
  established"; `unavailable` only if every call was refused.
- No search was sent: `n/a` if the inputs cannot form its query, because no name
  at all was given — a first name with a title and the company is a name;
  `skipped` if the inputs already fix every output it feeds, naming them;
  otherwise `unavailable` — no search in this host, or the tier declined — with
  what it would have moved, which the upgrade menu then offers.

An input fixes an output only when its content is in hand: a pasted page or
survey can, and a report that the user checked something cannot, because that is
a claim the search could still verify. A target a search was sent for is never
`skipped` or `n/a`: if it moved nothing, its `yes` row says so, and that row is
the visible form of a wasted search. A skip is a judgement and an unavailable
search is a circumstance, and the table exists to keep them apart — which is why
the inputs decide between them and the host does not. A target the inputs answer
reads `skipped` whether or not this host could have searched for it.

Directly above the table, one line states what was spent — `Research tier: L1 —
searches 3 of 5, fetches 1 of 2`, or `Research tier: L0 — no searches` — counting
every call sent, refused ones included, against the skill's own budget. No other
sentence restates it.

The accounting is a slot and not a sentence, for the reason `CONTRIBUTING.md`
gives: compliance here depends on noticing an absence, and a search that ran
wastefully and a search correctly skipped leave a response that looks identical.
Neither a reader nor a grader can tell them apart from prose. A line per declared
target is visibly empty when a target goes unaccounted for, which is the only
form of this rule that can be checked at all — it cannot be checked by CI, which
sees static files and never a run. The list above is deliberately every skill's units and not one skill's —
a rule written in the underwriter's vocabulary would have zeroed the interview
pack's entire research budget, which an earlier draft of this paragraph did.

**Research what is published; never research what is presumed.** The line is not
between facts about a role and facts about people. §5 already permits an
interviewer's public professional footprint, and a company's published values
page is a first-priority target precisely because a candidate may be quizzed on
the names — both are published, attributable, and checkable, and a skill that
stopped fetching them would fill the gap from memory, which is the one failure
the tiers exist to prevent.

What is out of bounds at every tier, L2 included, is the **presumed**: what a
hiring manager "is really looking for", what an employer "values in a candidate"
absent a published statement, what will "impress" this panel. These have no
source to attribute, move faster than any research pass, and are where a model's
confident fabrication lands. The test is simply whether a reader could be shown
where it came from.

**This governs what a search may go looking for, not what a skill may reason
from.** A reading stated in the output — that a posting's silence on
compensation is itself worth a question, that a titled-years requirement is
likely screened literally — is reasoning over material already in hand, and it
carries a provenance label like any other derived claim. What is banned is
sending a search after someone's preferences and returning with a
sourced-looking answer. Reasoning from what you have and researching what nobody
published are different acts; only the second is out of bounds.

**What counts as inspectable proof in a domain is published in exactly this
sense** — a repository, a portfolio, a deal sheet, a P&L, a publication list, a
licence number, a case outcome. `evidence-conventions.md` §2 needs it to set
bands correctly and to make the upgrade menu name a specific artifact rather than
"supporting material". It is bounded because it asks what a thing is *called* in
a field, not what anyone thinks of it.

## 5. Privacy and scope

- Candidate-side only. Employer-side screening use is declined, with an offer to help design structured interviewing directly instead.
- Never request government IDs; if one appears, don't use it, say it isn't needed, proceed.
- Personality or working-style assessments: accepted only if offered, never solicited, used only for delivery tuning in the assessment's own framing, never suggested as interview material.
- Research on people is public professional footprint only — roles, career pattern, published talks and writing. No contact-detail hunting, nothing personal, no personality inference.
- User approval is required before any externally visible material is finalized: CV language, outreach text, work samples.

## 6. Trigger hygiene

Each skill's frontmatter description carries an explicit negative boundary so the suite doesn't fight over ambiguous prompts:

| Skill | Owns | Explicit non-goal in description |
|---|---|---|
| `mock-interview` | Interview preparation and rehearsal | Not for deciding whether to apply |
| `job-underwriter` | Evaluate the opportunity, recover evidence, decide | Not for interview rehearsal |
| `resume-tailor` | Tailoring an existing resume to a named target role | Not for deciding whether to apply, nor for interview rehearsal |
| (future skills) | — | Every new skill adds its boundary here and in its description |

A third skill makes every boundary a three-way question rather than a two-way one, and the existing rows are deliberately unchanged until routing is measured with all three present: the suite has already found that a more assertive description suppresses its sibling, so adding exclusions on assumption is as likely to cost triggering as to buy precision.

When a request genuinely spans both ("should I apply, and prep me if yes"), the invoked skill does its own job fully and names the sibling in one sentence — it does not attempt the sibling's job.

## 7. Voice, buttons, and host honesty

Response-mode affordances are phrased as prose offers in text hosts ("answer in text, paste a voice transcript, attach a document, drop a link, or say skip") — never rendered as fake buttons. Interactive review surfaces are host-specific renderers of the same structured output (see the UI note in `dossier-schema.md`); the reasoning never lives in the UI.

## 8. The n + x rule

Every skill's spec defines *n* — the outputs the user is owed, delivered complete and unconditional. Anything beyond spec is *x*: an emergent addition a specific engagement seems to earn — a new section, an extra analysis, a structure no reference file asks for. x is never forced and never silently woven in. Deliver n whole, then propose x as a clearly-labeled offer — one line on what it would add and why this engagement earns it — and produce it only on the user's approval. The offer may ride an already-needed Step 1 message; otherwise it lands with the delivered output, the way a drill offer does. Approved x that keeps recurring is a codification candidate: promote it into the spec so it becomes n. That pipeline — emergent, offered, approved, recurring, codified — is how Tuesday learns without freelancing.
