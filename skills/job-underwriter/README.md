# job-underwriter

A Claude skill that underwrites a specific job opportunity: it evaluates the role against your real evidence, recovers overlooked-but-truthful experience your CV omits, classifies each gap (a presentation problem, a discovery problem, transferable-adjacent work, a genuine capability gap, or a failed hard gate), independently assesses the opportunity itself for risks and red flags, and delivers a go / conditional-go / hold / no-go decision with an evidence-backed application plan. Never a single fit score, never an invented claim — every conclusion traces to a source or is labeled as inference.

Part of [Tuesday](../../README.md), an applicant-side evidence system for job seekers. Fully standalone — Tuesday's shared artifacts (like the dossier) enhance this skill; they never gate it.

## Install

Skills require code execution to be enabled. Steps below are current as of mid-2026; if a menu has moved, see https://support.claude.com (search "skills").

**Web — claude.ai**
1. Free/Pro/Max: Settings → Capabilities → enable "Code execution and file creation". Team/Enterprise: an owner enables Code execution and Skills under Organization settings → Skills.
2. Customize → Skills → upload the zip (the zip root must be the `job-underwriter/` folder itself, not loose files), then toggle it on.
3. Uploaded skills are private to your account unless an org owner provisions them organization-wide.

**Desktop app**
Skills are account-level — anything enabled on claude.ai is already available; manage from Customize in the sidebar. Shortcut: if someone shares the packaged `.skill` file in a chat, the file card shows a "Save skill" button. Cowork sessions sync the skills enabled on your account at session start.

**Claude Code (CLI)**
Filesystem only — copy the `job-underwriter/` folder to:
- `~/.claude/skills/job-underwriter/` — personal, available in every project, or
- `.claude/skills/job-underwriter/` — project-scoped, committed to the repo so teammates get it on clone.

New sessions pick it up automatically; it is also invokable directly as `/job-underwriter`.

## First prompt

You don't need to name the skill — "should I apply to this?" with a JD matches its description and auto-triggers. The ideal first prompt front-loads what the skill would otherwise ask:

```
Should I apply to this? [JD pasted or attached]
My CV is attached. I'm at the [evaluating / applying / interviewing] stage.
Non-negotiables: [comp floor, location/remote, authorization, schedule].
[Optional: portfolio link, prior resume, "do the deeper research pass."]
```

The bare minimum also works — a JD and a fit question — you'll get a first-pass underwriting immediately, plus at most three questions aimed at whatever would most change the decision.

## What to provide

| Tier | Inputs | If missing |
|---|---|---|
| Required | The job description | The skill can't underwrite without the role |
| Sharpens | Your CV (or background in prose), your non-negotiables | Fit side degrades to a self-assessment worksheet; hard-gate checks marked unknown |
| Optional | Portfolio, repos, prior resumes, reviews, work samples, a `tuesday-dossier.md` from an earlier session | Confidence stays where the evidence supports it — the upgrade menu says exactly what each artifact would unlock |

The skill asks at most three questions per turn, always alongside an updated analysis, and proceeds if you ignore them. It never re-asks, and "skip" is always an accepted answer.

**Privacy by design:** never upload government IDs — the skill refuses them. Candidate-side only; it declines employer-side screening use. Research on named people is public professional footprint only.

## The dossier

At the end, the skill offers (never forces) a `tuesday-dossier.md` — a human-readable underwriting report with a machine-readable envelope at the bottom. Carry it into a mock-interview session and the prep pack starts from your verified evidence, your likeliest objections, and the risks worth validating live, instead of from scratch.

## What's in this folder

```
job-underwriter/
├── SKILL.md                            # the skill itself — instructions Claude follows
├── references/
│   ├── evidence-model.md               # evidence vocabulary, map row shape, confirmation card
│   ├── gap-taxonomy-and-questions.md   # five gap types, recovery patterns, question selection
│   ├── risk-and-decision.md            # signal classes, red-flag patterns, decision semantics
│   ├── dossier-template.md             # emission rules + full worked tuesday-dossier.md
│   ├── evidence-conventions.md         # mirror of conventions/ — source types, bands, labels
│   ├── reframing-audit.md              # mirror of conventions/ — six drift axes, five disciplines
│   ├── interaction-grammar.md          # mirror of conventions/ — standalone invariant, research tiers
│   ├── output-discipline.md            # mirror of conventions/ — six rules on a response's shape
│   ├── dossier-schema.md               # mirror of conventions/ — the shared dossier's schema
│   └── citations.md                    # mirror of conventions/ — sources behind the outside claims, verbatim
└── evals/
    └── evals.json                      # 3 test fixtures with verifiable expectations
```

`evals/` holds development fixtures and is excluded from the installable `.skill` package. `README.md` rides along inside the package but is inert at runtime — Claude only loads files that `SKILL.md` points to.
