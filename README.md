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
| **Planned third** | `skills/resume-tailor` | Evidence-locked resume tailoring — consumes verified evidence and prohibited claims; the showcase for the human-review UI pattern |
| **Absorbed** | Employer-question strategy, interview research briefs, answer coaching | Already live inside the two skills above (reverse questions + risk-verification questions; research tiers + interviewer reads; drill mode) |
| **Deferred, trigger stated** | Application tracker (trigger: repeated real use — it's a persistence product), work-sample strategist (first life: an underwriter plan section), networking/outreach, search diagnostician (needs tracker data) | Built when their triggers fire, not before |

## The cloth

Coherence lives in [`conventions/`](conventions/) — canonical, and mirrored into each skill's `references/` with a synced-from header (canonical wins on conflict):

- [`evidence-conventions.md`](conventions/evidence-conventions.md) — evidence source types, confidence bands, the gap taxonomy, content provenance labels, and the mapping that connects them. The truthfulness core every skill is bound by.
- [`interaction-grammar.md`](conventions/interaction-grammar.md) — the standalone invariant, elicitation policy, degradation and upgrade menus, research tiers, privacy and scope, trigger hygiene.
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

- **Skill triggering strength — measured, half fixed, not closed.** Under a corrected harness the original descriptions fired on 8 of 24 positive runs and on none of the 6 spanning runs. Rewriting job-underwriter's description — the candidate's own trigger phrases first, and the sibling boundary rewritten to admit a spanning request rather than exclude it — took that skill from 2/12 to 10/12, replicated across two independent runs. Nothing did the same for mock-interview: three rewrites all measured at or below the original, and swapping its description back to the original under the improved job-underwriter changed nothing (2/12 either way), so its description ships unchanged — a rewrite with no demonstrated benefit is how a suite accumulates churn. The four near-miss negatives stayed 12/12 in every configuration, so none of this bought triggering at the cost of over-triggering. What remains open is the more interesting half: mock-interview fires on roughly a fifth of its own reserved phrasings, and spanning requests reach a sibling on 2 runs of 6. Both track how assertive the *other* description is, and no run ever fired the wrong skill — the model is not confusing the two, it is declining to choose between them — so the next move is a property of the pair, not of either description alone.
- **Clean-room validation — closed, and it earned the wait.** `evals/run_fixtures.py` runs each skill's own fixtures in a project containing only that skill, and grades them with adversarial graders that see the response and the expectations but never the skill. All eight fixtures now run there. It found one defect worth the whole exercise: mock-interview answered two of five fixtures with clarifying questions and *no pack*, which its own Step 1 licensed and which not one of its 45 expectations could see, because none of them asserted that the first response delivers anything. job-underwriter had carried that expectation since v0.1, which is why one skill degraded gracefully outside the authoring context and the other collapsed. Also found and fixed: risk-register entries losing their verification questions wherever the register was rendered as a compact table, provenance labels vanishing entirely in a run with no web access, and a coined confidence value (`split`). Two of the defects were in the harness, not the skills — grading a cover note instead of the 27,000-character pack it described, then looking for that pack in the wrong directory and briefly making a skill that had delivered look like one that falsely claimed to. Six expectations turned out to be testing the environment or the old behaviour rather than the skill, and were rewritten. Re-running is one command, so this stays closed rather than drifting.
- **mock-interview voiced drill** — back-and-forth spoken rehearsal as a drill-mode enhancement; deferred until the hosting surface offers a voice loop the skill can rely on.
- **Routing eval coverage — grows with the suite.** `evals/suite-routing.json` covers the two skills that exist. A third skill makes every existing case ambiguous again, so resume-tailor (or any successor) ships with its own positives, its own near-miss negatives, and a re-run of the whole set — routing is a property of the list, not of any one entry.
