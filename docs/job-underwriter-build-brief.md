# Job Underwriter — build brief (v0.1)

Companion to `docs/job-underwriter-spec-v0.md` (carried verbatim from the authoring thread, August 2026). The spec is the design; this brief is the build contract. **Where they conflict, this brief wins** — it encodes four adjustments agreed in design review after the spec was written, plus the Tuesday conventions the spec predates.

## 1. Mission and ground rules

Build `skills/job-underwriter/` in this repository, v0.1, using the skill-creator skill's own loop (init → draft → run fixtures → iterate → package). Work on branch `skill/job-underwriter`, commit granularly, open a PR for owner review — do not merge it yourself. Never force-push. Do not modify `skills/mock-interview/` or `conventions/` in this build, with one sanctioned exception defined in §7. Any change to skill source re-triggers a `dist/` rebuild before the PR is final.

## 2. Read first, in this order

1. This brief, whole.
2. `docs/job-underwriter-spec-v0.md` — the full design: purpose, evidence model, gap taxonomy, recovery flow, risk register, decision logic, schema, edge cases, incorrect behaviors (`job-underwriter-spec-v0.md` §13).
3. `conventions/` — all three files. Binding, not advisory. This is the first skill *born* under them.
4. `skills/mock-interview/` — the house-style exemplar: SKILL.md length and register, frontmatter description style (trigger-rich, with an explicit negative boundary), references/ layout, evals/evals.json schema-in-practice.
5. skill-creator's own SKILL.md and its schemas reference, in whatever location your session has it installed — follow its formats for init, evals, and packaging. **Do not assume the file paths from any prior session; discover them locally.**

## 3. The four adjustments (these override `job-underwriter-spec-v0.md` §14's deliverables list)

1. **Skill-anatomy reshape.** Deliverables are `SKILL.md` + `references/` + `evals/evals.json`. The spec's `output-schema.json` and worked examples live inside `references/`; `tests/acceptance-tests.md` becomes eval expectations; **no `ui-contract.md`** in v0.1 (Phases 0–2 forbid building UI — the spec document remains Phase 4's source of truth); **no scripts** — nothing in this skill computes deterministically, so nothing should exist to rot.
2. **One dossier, not six files.** The output artifact is a single `tuesday-dossier.md` per `conventions/dossier-schema.md`: human-readable report on top, one fenced JSON envelope (`dossier_version: "1.0"`) at the bottom. The spec's six objects are *sections* of that envelope. Include `handoff_to_mock_interview` exactly per schema §6.
3. **Analysis leads; questions ride.** The first response contains a first-pass assessment built from whatever was provided, in the same message as any orientation questions. Never open with a questions-only or consent-only message. Subsequent turns are adaptive (this skill's product *is* iterative recovery): each turn = updated analysis first, then at most three highest-value questions ranked by the spec's heuristic (importance × uncertainty × recovery probability × decision impact ÷ user effort). Proceed on silence; never re-ask; deep-research consent rides, never drives.
4. **Response modes are prose offers.** "Answer in text, paste a voice transcript, attach a document, drop a link, or say skip." Never render bracketed pseudo-buttons in a text host.

## 4. Conventions bindings — the explicit checklist

- **Standalone invariant** (grammar §1): full value from a JD + CV alone; a dossier or prior pack in context is an enhancer. Dossier behavior is read-if-present, append-always-*offered*, never required.
- **Vocabulary verbatim** from `evidence-conventions.md`: source types (§1), confidence bands (§2), fit statuses and the five gap types (§3), provenance labels (§4), and the §5 mapping with its two overrides (prohibited claims absolute; hard gates never buried). Do not coin synonyms; the suite has one dialect.
- **Truthfulness core** (§6) binds every output — including the "never a single numeric fit score" rule.
- **Research tiers** per grammar §4 and the skill's own targets: L0 docs-only; L1 default with a stated budget; L2 offered once, cost stated, consent-gated; the not-attributable rule applies (name collisions and stealth companies get archetype fallback, said plainly).
- **Privacy and scope** (grammar §5): candidate-side only; no government IDs (check content, not filename); people research is public professional footprint only.
- **Trigger hygiene** (grammar §6): the table already reserves this skill's row — the frontmatter description **must** carry the negative boundary "not for interview rehearsal" and should carry pushy positive triggers ("should I apply", "am I a fit for this JD", "evaluate this role against my resume", "is this posting worth pursuing", JD+CV uploaded with a fit question). Description drift against that table is the defect class this suite explicitly hunts.
- **The n + x rule** (grammar §8): include an operative copy in SKILL.md, phrased like mock-interview's — pre-mirror duplication is the accepted pattern until the mirror mechanism ships in mock-interview v2. Deliver spec sections whole; anything a run invents beyond them arrives as a labeled offer.

## 5. Proposed anatomy (builder may adjust names, not the coverage)

```
skills/job-underwriter/
├── SKILL.md                      # workflow, input contract, elicitation, guardrails, n+x
├── LICENSE                       # copy per CONTRIBUTING rule — .skills travel self-describing
├── README.md                     # human-facing; "Part of Tuesday" line + standalone invariant
├── references/
│   ├── evidence-model.md         # per-requirement evidence_map shape; JSON envelope; worked micro-examples
│   ├── gap-taxonomy-and-questions.md  # five gap types → recall-prompt patterns; question-selection heuristic; response-mode offers
│   ├── risk-and-decision.md      # opportunity risk register semantics; capability-vs-opportunity separation; go / conditional_go / hold_pending_answers / no_go
│   └── dossier-template.md       # the full worked tuesday-dossier.md example — schema v1.0's first stress test
└── evals/
    └── evals.json
```

## 6. Evals — fixtures and expectations

Three fixtures straight from spec Phase 2, self-contained prompts: **direct-fit**, **adjacent-pivot**, **suspicious-role** (the suspicious-role fixture may use a fictional posting with planted red-flag language; a real public company is acceptable only where live research is the point). Expectations must include, beyond happy-path structure:

- **Negative expectations from `job-underwriter-spec-v0.md` §13:** output contains no single numeric fit score; never suggests adding an unverified claim to the CV; a hard-gate failure surfaces in the decision snapshot regardless of fit elsewhere; a memory-style lead is never converted into asserted experience.
- **Process expectations:** the first response contains a first-pass assessment, not questions alone; no turn asks more than three questions; the dossier is offered at the end; any beyond-spec addition arrives as a labeled n+x offer, not woven in.
- **Vocabulary expectations:** gap types, confidence bands, and provenance labels appear using the conventions' exact terms.

## 7. The dossier feedback loop — the one sanctioned conventions touch

The worked dossier in `references/dossier-template.md` is schema v1.0's first real stress test. If field-level friction surfaces, amend `conventions/dossier-schema.md` **canonical-first, in the same PR**: additive change → note it as 1.1; breaking change → 2.0 plus a migration note appended to the schema doc. Never fork a private dialect inside the skill — a skill that quietly disagrees with the canonical is the drift this repo's whole structure exists to prevent.

## 8. Definition of done

1. Packager validation passes; `dist/job-underwriter.skill` built and committed.
2. All three fixtures run in-session with results honestly graded against expectations — including failures, reported as findings, not silently fixed into the fixtures.
3. `grep -ril` across the new skill for real-person data returns nothing; all fixture people and companies fictional or public-generic.
4. Repo updates in the same PR: README ecosystem table row for job-underwriter moves from **Next** to shipped-status wording; README Tracked-work ledger updated (this build closes its own line and does not silently close others); trigger-hygiene expectations verified against the actual frontmatter description.
5. PR description states: what conformed to spec, what the four adjustments changed in practice, any n+x candidates observed during fixture runs (proposed, not applied), and any schema amendments made under §7.

## 9. Host notes (Claude Code)

- Use skill-creator's scripts wherever this session finds them installed; no hardcoded paths from other environments.
- L2 here means an expanded search budget within the same targets — there is no separate deep-research feature to hand off to; the research-checklist convention already words it this way.
- `memory_lead` stays in the vocabulary regardless of host: in this session it covers anything recalled from prior context rather than confirmed by the user now. The rule is host-independent: leads prompt questions; they are never evidence.
- The finished skill will also be invokable as `/job-underwriter` in Claude Code — one line in its README install section, mirroring mock-interview's.

## 10. Out of scope for v0.1

mock-interview v2 (mirror, handoff consumption, `pack_feedback`) — separate change, next on the ledger. CI. Anything UI (Phase 4). `agent/`. Resume-tailor seams beyond what the schema already reserves.

## 11. Decisions reserved

- Exact description phrasing (within §4's constraints) — builder drafts, owner approves in PR review.
- Fixture company choices — builder's call within §6's rules.
- Reference-file naming — builder's call; coverage is not negotiable.
