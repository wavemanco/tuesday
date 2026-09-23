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

- **L0** — provided documents only. Everything else labeled `[generic]`.
- **L1** — default: a small budgeted set of targeted searches (each skill defines its targets and caps). Official sources first; freshness rules per fact class; model memory is never a source for values, processes, or current facts.
- **L2** — deep research: offered exactly once, cost stated, run only on consent; the offer rides an already-needed message or lands in the upgrade menu.
- **Not-attributable rule:** results that can't be attributed to the specific entity (name collisions, no web presence) are treated as not-established — said plainly, archetype fallback named, missing facts listed in the upgrade menu.

**Depth is bounded by what the answer can change.** A search that cannot move a
row, a band, a gap type or a recommendation does not run, whatever budget is
left. This is what the tiers were always implementing, and it is stated because
the tiers describe *how much* and not *what for*: L1's cap is a ceiling, not a
target, and a skill that spends it on questions whose answers change nothing has
followed the letter and missed the point. Name the cell a search could change
before running it; if there is no such cell, skip it and say what was skipped.

**Research the artifact vocabulary, not the employer's preferences.** What counts
as inspectable proof in a domain — a repository, a portfolio, a deal sheet, a
P&L, a publication list, a licence number, a case outcome — is a bounded question
with a checkable answer, and `evidence-conventions.md` §2 needs it to set
confidence bands correctly and to make the upgrade menu specific. What employers
"value", "look for" or "want to see" is unbounded, moves faster than any research
pass, and is precisely where a model's confident fabrication lands; **it is not a
research target at any tier, L2 included.**

The difference is worth stating because the two questions sound alike: the first
asks what a thing is *called* in this field, the second asks what someone
*thinks*. The first has a right answer that a reader can verify. The second
produces a sentence that sounds like a finding, cites nothing, and is `[generic]`
at best — which `evidence-conventions.md` §5 now forbids from carrying weight.

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
