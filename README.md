# Tuesday

Tuesday is an applicant-side evidence system, shipped first as a suite of Claude skills. The system's job: help a job seeker evaluate opportunities on evidence rather than vibes, recover truthful evidence their CV omits, prepare for real interviews, and never — at any point — coach a claim the evidence doesn't support.

Skills are the first surface. A later orchestrating agent is a stated destination of the same repository, consuming the same contracts (see *Repository shape* and *Licensing*).

## Why "Tuesday"

Tuesday is *Mangalvaar* in Hindi — the day of Mangal, which names Mars and is also a word for auspiciousness. An auspicious day belonging to the god of war is exactly this system's register: it puts the applicant on a deliberate, well-armed path to the right opportunity rather than a spray of hopeful applications — and the only ammunition it ever issues is verified evidence. (Job-market folklore also holds that postings and applications peak on Tuesdays; treat that as a wink, not a citation.)

## The one rule

**Every skill stands alone.** Each runs to a complete, useful output from raw inputs (a JD, a CV, a prompt). Artifacts from sibling skills enhance; they never gate. Use one skill, use them all, use them in any order — the shared dossier makes order irrelevant, not mandatory.

## What's here, what's next

| Status | Skill | What it does |
|---|---|---|
| **Shipped** | [`skills/mock-interview`](skills/mock-interview/) | Persona-categorized interview prep packs with grounded per-question guidance, fit-gap mapping, values alignment, reverse questions, and live drill mode |
| **Shipped** | [`skills/job-underwriter`](skills/job-underwriter/) | Evaluate a specific role, recover overlooked truthful evidence, classify real gaps vs. CV omissions, surface opportunity risks, and reach a go / conditional-go / hold / no-go decision — with an offered `tuesday-dossier.md` that hands verified evidence to mock-interview |
| **Shipped** | [`skills/resume-tailor`](skills/resume-tailor/) | Evidence-locked resume tailoring — an edit ledger where every proposed change traces to a sentence the candidate wrote, a coverage map that names what the resume cannot support, a parse-safety check, and a refusal to write hidden text for automated screeners. Nothing is applied until approved |
| **Planned fourth** | — | Nothing is next by default. The deferred list below is trigger-gated, and the suite's own measurement says a fourth skill makes every routing case ambiguous again |
| **Absorbed** | Employer-question strategy, interview research briefs, answer coaching | Already live inside the two skills above (reverse questions + risk-verification questions; research tiers + interviewer reads; drill mode) |
| **Deferred, trigger stated** | Application tracker (trigger: repeated real use — it's a persistence product), work-sample strategist (first life: an underwriter plan section), networking/outreach, search diagnostician (needs tracker data) | Built when their triggers fire, not before |

## The cloth

Coherence lives in [`conventions/`](conventions/) — canonical, and mirrored into each skill's `references/` with a synced-from header (canonical wins on conflict):

- [`evidence-conventions.md`](conventions/evidence-conventions.md) — evidence source types, confidence bands, the gap taxonomy, content provenance labels, and the mapping that connects them. The truthfulness core every skill is bound by.
- [`interaction-grammar.md`](conventions/interaction-grammar.md) — the standalone invariant, elicitation policy, degradation and upgrade menus, research tiers, privacy and scope, trigger hygiene.
- [`reframing-audit.md`](conventions/reframing-audit.md) — six axes of drift and five disciplines, covering every word a skill proposes the candidate say, write, or send. Canonical because it is not one skill's property: job-underwriter proposes resume lines and outreach phrasing, resume-tailor's whole output is proposed language, and two copies of it would diverge in exactly the two places it is load-bearing.
- [`output-discipline.md`](conventions/output-discipline.md) — five rules on the shape of a delivered response, each learned from a measured defect. Every rule separates an **invariant** the suite holds absolutely from a **parameter** each skill declares for itself, because the half that kept failing was never the number: two skills already said "at most three questions" and what broke was that a question inside a template did not feel like it counted. Skills declare their parameters in a `## Output discipline` block and CI fails a skill that omits one — a default nobody chose is the failure this file exists to prevent.
- [`dossier-schema.md`](conventions/dossier-schema.md) — the versioned shared artifact: read-if-present, append-always-offered, never required. One writer per section; handoffs in both directions.

## Install

Per-skill instructions live in each skill's README. The short version:

- **claude.ai (web):** enable code execution (Settings → Capabilities), then Customize → Skills → upload the skill's zip. The zip root must be the skill folder itself.
- **Desktop app:** skills follow your claude.ai account (Customize in the sidebar); a shared `.skill` file card offers one-click Save.
- **Claude Code (CLI):** copy `skills/<name>/` to `~/.claude/skills/` (personal) or commit to `.claude/skills/` in a project. Also invokable as `/<name>`.

Prebuilt installables live in [`dist/`](dist/) (`.skill` files; rebuildable from source — may graduate to GitHub Releases).

## Repository shape

```
conventions/        canonical contracts — the cloth
skills/<name>/      self-contained skill packages (SKILL.md, references/, evals/, docs/)
evals/              suite-level evals — routing between skills, which no single skill can test
ci/                 repository checks, standard-library only, with their own self-test
dist/               built .skill installables
agent/              (reserved — does not exist yet; arrives when its trigger fires)
```

Skills are dependency-free by rule: nothing outside a skill's folder is required at runtime, because installation is per-skill. The conventions are therefore a canonical-plus-mirrors system, not a runtime import; mirror drift is a defect.

## Licensing

Per-directory licensing, mapped in the root [`LICENSE`](LICENSE). Current staging, per the maintainer's working decision (finalize before any public release): `conventions/` and `skills/*` under MIT so the skills travel maximally; `agent/` is reserved for a copyleft grant (AGPL) decided when it exists. GitHub's sidebar shows a single license badge — the root LICENSE file is the authority. Contribution terms, including the CLA reservation for `agent/`, are in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Tracked work

- **Skill triggering strength — measured across three skills, and my own explanation for it was wrong.** With two skills the rates were lopsided: job-underwriter 10/12 of its own reserved phrasings, mock-interview 2/12. This ledger recorded the obvious reading — that the two compete, and mock-interview's rate tracked how assertive job-underwriter's description was, since it moved when job-underwriter's changed and not when its own did. Adding a third skill falsifies it. mock-interview went **2/12 → 7/12 without a word of its description changing**, job-underwriter 10/12 → 7/12, resume-tailor arrived at 4/12. The rates converged rather than compounding, which a competition model does not predict. The honest reading now is that each skill fires around half the time on its own reserved phrasings, that the two-skill split was a smaller sample than it looked, and that I do not have a mechanism — only a measurement. Spanning requests remain the weakest case at 1 reach in 9.
- **No over-triggering, and no confusion between skills — 63 runs, three skills.** Every near-miss negative held: 18/18 across six cases, including the two sharpest in the set, a template redesign and a proofread that wear resume-tailor's exact vocabulary. And **not one run in the entire suite has ever fired the wrong skill.** The model is not mixing these up; where it fails, it answers directly instead of reaching for any of them.
- **Three-way trigger boundaries — measured, and the answer is to change nothing.** `interaction-grammar.md` §6 carries resume-tailor's row; job-underwriter's and mock-interview's boundaries still name only each other, and stay that way. The reason to add a third exclusion to each would be cross-firing, and there is none to fix — while the cost is well evidenced, since this suite has already watched a more assertive description move its sibling's rate. Reserved decisions get made on measurement or not at all.
- **Provenance labels — closed, structurally.** Four prose rules failed to keep `[grounded]`/`[inferred]`/`[generic]` attached to derived claims. What worked was giving the label a column: role reality, the risk register and the application plan are now tables with a Provenance cell, and graders report the labels present in every run of every section that has one. The general finding is worth more than the fix — **where a section is a table the rule holds; where it is prose, four rules across four commits could not make it hold.** The corollary shipped with it: a label marks where a claim about the *world* came from, not the skill's reasoning about its own analysis, and the test is whether the sentence would still assert something if the analysis were deleted.
- **Clean-room failures are classified, not counted.** `run_fixtures.py` runs each fixture once, re-runs any fixture that failed something twice more, and reports each failure as `deterministic` (failed every run) or `intermittent`. On its first real use that separated 1 real defect from 7 draws on 14 executions rather than 24 — and caught two contradictions between rules I had written myself, both invisible while every failure looked alike. mock-interview eval 5, the fixture this ledger flagged as unstable, now reads 13/13 from both graders. Two harness lessons are in `evals/README.md`: grade the artifact rather than the cover note, and never let a grader that returned nothing count as a run in which everything failed.
- **mock-interview's spec — written, and it found three things.** `docs/mock-interview-spec-v1.md`, versioned v1 rather than v0 because it describes a skill that already shipped. Writing it was not archaeology: the skill's own `n + x` rule opens *"the sections this skill's spec defines are n"* and had been pointing at a document that did not exist since the day it was written, which is exactly the blind spot the Step 1 defect lived in. Three gaps surfaced, all proposed rather than built: a pack made **without** a dossier has no prohibited-claims record, though the other two skills both maintain one locally and the same temptations exist; the drill's scoring rubric is specified somewhere the skill body never points at; and **loop mode has no fixture at all** — five cover session mode, none covers multiple scheduled rounds, which is the kind of gap that stays invisible until someone uses the feature.
- **Cross-set recurrence — a signal the runner is blind to, and it corrected me twice.** `evals/recurring.py` reads grade JSON that clean-room runs already wrote and finds expectations failing across *independent* run-sets. The runner classifies within one set, so a failure appearing once in every three runs reads as intermittent noise each time; holding at that rate across three sets is a stable defect. Two claims of mine did not survive it. The question-budget and sibling-count fixes went from deterministic to **50% across two sets** — real improvement, not the closure I reported. And resume-tailor's altered-quote failure sits at **33% across all three sets including the most recent**, where I had described it as fixed and dropped to intermittent. All three have now had one rewording and persisted, which by `CONTRIBUTING.md`'s own rule means the next fix changes the shape. The question budget has an obvious slot — number the questions and state the count, so counting is forced rather than remembered — and the other two do not yet.
- **mock-interview voiced drill** — back-and-forth spoken rehearsal as a drill-mode enhancement; deferred until the hosting surface offers a voice loop the skill can rely on.
- **Routing eval coverage — grows with the suite.** `evals/suite-routing.json` covers the two skills that exist. A third skill makes every existing case ambiguous again, so resume-tailor (or any successor) ships with its own positives, its own near-miss negatives, and a re-run of the whole set — routing is a property of the list, not of any one entry.
